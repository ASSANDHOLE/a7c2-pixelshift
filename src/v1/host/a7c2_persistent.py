"""User-operated, fixed-candidate persistent install/undo. Offline by default.

Only explicit live subcommands can open USB. No shutter, calibration, raw-flash,
generic path, generic payload or automatic restart operation is available.
"""
import argparse,json,os,shutil,sys
from contextlib import ExitStack
from pathlib import Path
from acquire import ROOT,sha256
from a7c2_readonly import preflight as reader_preflight,load_keys,UsbSystem,SessionFiles,exclusive_session,private_root
from a7c2_readonly_protocol import Protocol,NORMAL_PID,SERVICE_PID
from a7c2_readonly_backup import parse_snapshot,identity_digest
from a7c2_cp_reader import expected_body
from persistent_pixelshift_v1 import OUT,digest
from prepare_persistent_writer import BUILD
from check_persistent_package import identify
from persistent_writer_protocol import WriterProtocol,request,parse,STAGING,REQUEST,RESULT,PROGRAMS

PRIVATE=ROOT/'data/private/sessions'
REVIEW=ROOT/'integrity/runtime-review.json'
CAL_KEYS=(0xf0011,0xf0025,0xf0028)

def save(folder,state):
    p=folder/'state.json.partial'
    with p.open('w') as f:json.dump(state,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
    p.replace(folder/'state.json')

def package():return json.loads((OUT/'manifest.json').read_text())

def expected_files(cp):return {'AP':'unchanged','CP':cp}

def preflight():
    reader_preflight();r=json.loads(REVIEW.read_text())
    if r['status']!='offline-passed' or r['camera_tested']:raise ValueError('Writer review is not an offline release')
    for row in r['files']:
        if sha256(ROOT/row['path'])!=row['sha256']:raise ValueError('Changed since writer review: '+row['path'])
    m=package()
    for c in m['components']:
        if sha256(ROOT/c['stock_source'])!=c['stock_sha256'] or sha256(ROOT/c['candidate_path'])!=c['candidate_sha256']:raise ValueError('Candidate/source hash differs')
    return dict(status='PACKAGE_READY',camera_access=False,changed_bytes=3,write_bytes=12,write_ranges=3,development_hardware_evidence=r['hardware_evidence'],package_version=r['package_version'])

def new():
    preflight();PRIVATE.mkdir(parents=True,exist_ok=True);f=SessionFiles(PRIVATE,'session')
    state=dict(schema=1,phase='new',manifest_sha256=sha256(OUT/'manifest.json'),review_sha256=sha256(REVIEW),body=expected_body(),pending=None,history=[])
    save(f.path,state);return f.path

def session(path):
    path=path.resolve()
    if not path.is_relative_to(PRIVATE.resolve()) or path.parent!=PRIVATE.resolve():raise ValueError('Use this writer session directory')
    s=json.loads((path/'state.json').read_text())
    if s['manifest_sha256']!=sha256(OUT/'manifest.json') or s['review_sha256']!=sha256(REVIEW) or s['body']!=expected_body():raise ValueError('Session/review/body binding changed')
    return path,s

def backup(service,files,state,label,memory):
    raw=service.snapshot(memory);files.snapshot(label,raw);blocks=parse_snapshot(raw)
    if identity_digest(blocks)!=state['body']:raise RuntimeError('Different camera body; stopped')
    selected={hex(k):dict(attr=blocks[1].properties[k].attr,data=blocks[1].properties[k].data.hex()) for k in CAL_KEYS}
    return selected

def read_programs(service,files,manifest,label,announce):
    states={}
    for row in manifest['components']:
        name=row['name'];announce(f'READBACK: {name} complete file ({row["bytes"]} bytes).')
        raw=service.read_file(PROGRAMS[name])
        if raw is None:raise RuntimeError(name+' program file missing')
        files.snapshot(label+'-'+name,raw);states[name]=identify(raw,row)
    return states

def clear_known_staging(service,expected_request,helper):
    for path,wanted in ((REQUEST,expected_request),(STAGING,helper)):
        raw=service.read_file(path)
        if raw is not None:
            if raw!=wanted:raise RuntimeError('Unowned staging file left untouched: '+path)
            service.delete_verified(path,raw)

def reconcile(service,files,state,folder,helper):
    pending=state.get('pending')
    if not pending:
        for path in (REQUEST,RESULT,STAGING):
            if service.read_file(path) is not None:raise RuntimeError('Unowned staging/report exists; preserve it: '+path)
        return
    expected=bytes.fromhex(pending['request_hex']);raw=service.read_file(RESULT)
    if raw is None:
        # Preserve available files as observations only. An in-flight writer
        # can make these mixed-time views; they do not authorize another write.
        for name,path in PROGRAMS.items():
            observed=service.read_file(path)
            if observed is not None:files.snapshot('pending-observed-'+name,observed)
        raise RuntimeError('Previous helper completion is still unknown. Available file observations were saved; no further helper or write was sent.')
    files.snapshot('reconciled-result',raw);report=parse(raw,expected);files.snapshot('reconciled-json',json.dumps(report,indent=2).encode())
    clear_known_staging(service,expected,helper);service.delete_verified(RESULT,raw)
    state['last_native']=report;state['pending']=None;state['phase']='needs-inspection'
    if report['action'] in (1,2):state['write_receipt']=report
    if report['action']==3 and not report['status'] and report['flags']&7==7 and report['image_mode']==0:state['snapshot_invalidated_boot']=report['boot_id']
    save(folder,state)

def invoke(service,files,state,folder,helper,action):
    if state.get('pending'):raise RuntimeError('Resolve the previous helper before another invocation')
    for path in (REQUEST,RESULT,STAGING):
        if service.read_file(path) is not None:raise RuntimeError('Staging path is occupied')
    raw_request=request(action);number=service.policy.calls;files.snapshot(f'native-{number}-request',raw_request)
    service.policy.arm(raw_request);service.upload(REQUEST,raw_request)
    if service.read_file(REQUEST)!=raw_request:raise RuntimeError('Request readback differs')
    state['pending']=dict(action=action,request_hex=raw_request.hex());save(folder,state)
    service.upload(STAGING,helper)
    raw=service.read_file(RESULT)
    if raw is None:raise RuntimeError('No complete helper report; outcome unknown')
    files.snapshot(f'native-{number}-result',raw);r=parse(raw,raw_request);files.snapshot(f'native-{number}-json',json.dumps(r,indent=2).encode())
    clear_known_staging(service,raw_request,helper);service.delete_verified(RESULT,raw)
    state['pending']=None;state['last_native']=r;save(folder,state);return r

def success(r):
    if r['status'] or r['readonly'] or r['cleanup']:raise RuntimeError(f'Native stage stopped: status={r["status"]}, rollback={r["rollback"]}, readonly={r["readonly"]}')

def finalize(service,files,state,folder,helper,expected,boot,announce):
    # A same-boot, successful drop/mode0 receipt can be reused when undoing
    # before the requested restart. Mode0 alone is not evidence of a drop.
    current=state.get('last_native',{})
    if current.get('image_mode')==0:
        if state.get('snapshot_invalidated_boot')!=boot:raise RuntimeError('Snapshot mode is already zero without this session\'s verified drop receipt; preserve state for review')
    else:
        announce('SNAPSHOT: invalidate the old startup snapshot; no restart command is sent.')
        r=invoke(service,files,state,folder,helper,3);success(r)
        if r['boot_id']!=boot or r['image_mode']!=0 or r['flags']&7!=7 or not r['snapshot_backend_valid']:raise RuntimeError('Snapshot completion contract differs')
        state['snapshot_invalidated_boot']=boot;save(folder,state)
    state.update(phase=expected+'-pending-boot',expected=expected,change_boot=boot);save(folder,state)

def work(stage,service,files,state,folder,helper,manifest,confirm_power_cycle=False,announce=print):
    reconcile(service,files,state,folder,helper)
    before_memory=backup(service,files,state,'before-memory',True)
    before_stored=backup(service,files,state,'before-stored',False)
    states=read_programs(service,files,manifest,'before',announce)
    announce('CHECK: verify model, Pixel Shift Off, loaded AP state and snapshot state.')
    r=invoke(service,files,state,folder,helper,0)
    # Undo can repair a /usr mount left rw after a previous cleanup failure.
    if not (stage=='undo' and r['status']==-30 and r['model']==16 and not r['mode'] and not r['cache']):success(r)
    boot=r['boot_id'];state['observed_files']=states;save(folder,state)
    if stage=='prepare':
        if states!=expected_files('stock') or r['loaded']!=1 or r['image_mode']!=2 or not r['snapshot_backend_valid']:raise RuntimeError('Preparation requires the exact installed v1 files/AP and native snapshot mode 2')
        state.update(phase='prepared',prepared_boot=boot,baseline_records=before_stored);save(folder,state)
    elif stage=='inspect':
        if states not in (expected_files('stock'),expected_files('candidate')):
            state['phase']='known-partial';save(folder,state);raise RuntimeError('Known incomplete program pair. Keep power/USB connected; only reviewed undo is permitted before restart.')
        if not state.get('pending'):state['phase']='inspected'
        save(folder,state)
    elif stage=='verify':
        if not confirm_power_cycle:raise RuntimeError('Verify requires the requested battery power cycle')
        expected=state.get('expected');desired='candidate' if expected=='installed' else 'stock' if expected=='restored' else None
        if desired is None or states!=expected_files(desired):raise RuntimeError('Files do not match the expected installed/restored state')
        if boot==state.get('change_boot'):raise RuntimeError('No new boot observed')
        if r['loaded']!=1:raise RuntimeError('Loaded AP differs from verified files; an old snapshot may remain active')
        state['phase']=expected;state['verified_boot']=boot;save(folder,state)
    elif stage in ('install','undo'):
        if stage=='install':
            if state['phase']!='prepared' or states!=expected_files('stock') or r['loaded']!=1:raise RuntimeError('Update requires a prepared v1 session')
            if before_stored!=state['baseline_records']:raise RuntimeError('Selected stored calibration/policy records changed since preparation')
            if r['image_mode']!=2 or not r['snapshot_backend_valid']:raise RuntimeError('Unexpected startup snapshot state before install')
        # Undo remains available for a known file pair even if a prior snapshot
        # finalizer failed. Finalization below still requires a valid receipt.
        state.update(phase='writing-'+stage,expected='installed' if stage=='install' else 'restored',change_boot=boot,
            write_pre_records=dict(memory=before_memory,stored=before_stored),write_receipt=None);save(folder,state)
        announce(('INSTALL' if stage=='install' else 'UNDO')+': checked offset writes; keep power and USB connected.')
        result=invoke(service,files,state,folder,helper,1 if stage=='install' else 2)
        state['write_receipt']=result;save(folder,state)
        after=read_programs(service,files,manifest,'after',announce);state['observed_files']=after
        if result['status']:
            if after==expected_files('stock') and not result['rollback'] and not result['readonly']:
                state['phase']='failed-restored';save(folder,state)
            raise RuntimeError(f'Writer reported {result["status"]}; readback states: {after}; rollback={result["rollback"]}')
        success(result);expected='installed' if stage=='install' else 'restored';wanted='candidate' if stage=='install' else 'stock'
        if after!=expected_files(wanted):raise RuntimeError('Complete file readback does not match requested result')
        state.update(phase='files-verified',expected=expected,change_boot=boot);save(folder,state)
        after_memory=backup(service,files,state,'after-memory',True);after_stored=backup(service,files,state,'after-stored',False)
        if before_stored!=after_stored or before_memory!=after_memory:raise RuntimeError('Selected calibration/policy records changed; keep service connection for review')
        r=invoke(service,files,state,folder,helper,0);success(r)
        if r['boot_id']!=boot:raise RuntimeError('Boot changed during file transaction')
        finalize(service,files,state,folder,helper,expected,boot,announce)
    elif stage=='finalize':
        expected=state.get('expected');wanted='candidate' if expected=='installed' else 'stock' if expected=='restored' else None
        if wanted is None or states!=expected_files(wanted):raise RuntimeError('Finalize requires the previously verified complete pair')
        receipt=state.get('write_receipt');prior=state.get('write_pre_records',{})
        if not receipt or receipt['status'] or receipt['readonly'] or receipt['boot_id']!=boot:raise RuntimeError('No successful same-boot writer receipt; do not skip an unresolved write error')
        if before_stored!=prior.get('stored') or before_memory!=prior.get('memory'):raise RuntimeError('Selected records differ from the file transaction')
        finalize(service,files,state,folder,helper,expected,boot,announce)
    else:raise ValueError('Stage')
    files.manifest.update(status='stage-complete',phase=state['phase'],native=r);files.save()

def live(stage,system,files,state,folder,helper,manifest,keys,already_service=False,confirm_power_cycle=False,announce=print):
    raw=service=None;error=None
    try:
        if not already_service:
            raw=system.normal();p=Protocol(raw,NORMAL_PID,keys,files.event);announce('NORMAL_AUTH: enter service once; keep USB connected.');p.authenticate();raw.close();raw=None
        announce('WAIT_SERVICE: waiting for Sony service identity 054C:0336.')
        raw=system.service();system.settle_service()
        actions={'prepare':{0},'inspect':{0},'verify':{0},'install':{0,1,3},'undo':{0,2,3},'finalize':{0,3}}[stage]
        service=WriterProtocol(raw,SERVICE_PID,keys,helper,actions,{r['name']:r['bytes'] for r in manifest['components']},files.event);service.authenticate()
        work(stage,service,files,state,folder,helper,manifest,confirm_power_cycle,announce)
    except BaseException as exc:
        error=exc;files.manifest.update(status='stopped',error=type(exc).__name__+': '+str(exc))
    finally:
        complete=state['phase'] in ('prepared','installed-pending-boot','restored-pending-boot','installed','restored','failed-restored','inspected')
        # An unsuccessful inspection must not turn a prior safe phase into an
        # automatic exit when current files/outcome could be uncertain.
        safe=not state.get('pending') and (error is None or state['phase']=='failed-restored') and complete
        attempted=False
        if safe and service and service.healthy and service.policy.state=='ready':
            attempted=True;announce('SERVICE_EXIT: returning to USB mode selection.')
            try:service.stop()
            except BaseException as ex:files.manifest['exit_error']=type(ex).__name__
        if raw:
            try:raw.close()
            except BaseException:files.manifest['close_error']=True
        if attempted:
            announce('WAIT_NORMAL_USB: select Image Transfer (MSC) if prompted; wait for completion.')
            try:files.manifest['exit_verified']=system.verify_normal_return()
            except BaseException:files.manifest['exit_verified']=False
        files.manifest['exit_attempted']=attempted;files.save();state['history'].append(dict(stage=stage,path=files.path.relative_to(folder).as_posix(),status=files.manifest['status']));save(folder,state)
    if error:
        announce('STOPPED: '+str(error));announce('Keep power/USB connected and logs. Do not restart or repeat install; use the inspection/recovery instructions.');return 2
    announce(f'STAGE_OK: {stage} | phase: {state["phase"]}');announce('NORMAL_USB_RETURN: '+str(files.manifest['exit_verified']));return 0

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('preflight');sub.add_parser('new');s=sub.add_parser('status');s.add_argument('--session',type=Path,required=True)
    for stage in ('prepare','install','undo','verify','inspect','finalize'):
        s=sub.add_parser(stage);s.add_argument('--session',type=Path,required=True);s.add_argument('--allow-camera-read',action='store_true',required=True);s.add_argument('--allow-helper-staging',action='store_true',required=True)
        s.add_argument('--firmware',choices=('2.01',),required=True);s.add_argument('--confirm-idle',action='store_true',required=True);s.add_argument('--already-service',action='store_true')
        if stage in ('install','undo','finalize'):s.add_argument('--allow-camera-write',action='store_true',required=True)
        if stage=='verify':s.add_argument('--confirm-power-cycle',action='store_true',required=True)
    a=p.parse_args(argv)
    if a.command=='new':print(new());return 0
    result=preflight()
    if a.command=='preflight':print(json.dumps(result,indent=2));return 0
    folder,state=session(a.session)
    if a.command=='status':print(json.dumps({k:state.get(k) for k in ('phase','pending','observed_files','expected','prepared_boot','change_boot','verified_boot')},indent=2));return 0
    if shutil.disk_usage(folder).free<1024*1024*1024:raise RuntimeError('Need 1 GiB free for complete readbacks and logs')
    helper=(BUILD/'persistent-writer.so').read_bytes();manifest=package();keys=load_keys()
    with ExitStack() as stack:
        stack.enter_context(exclusive_session(private_root()));stack.enter_context(exclusive_session(PRIVATE))
        files=SessionFiles(folder,a.command);print('Private run:',files.path,flush=True)
        return live(a.command,UsbSystem(files.event,lambda s:print(s,flush=True)),files,state,folder,helper,manifest,keys,a.already_service,getattr(a,'confirm_power_cycle',False),lambda s:print(s,flush=True))

if __name__=='__main__':
    try:raise SystemExit(main())
    except (Exception,KeyboardInterrupt) as exc:print('STOPPED:',type(exc).__name__+': '+str(exc),file=sys.stderr);raise SystemExit(2)

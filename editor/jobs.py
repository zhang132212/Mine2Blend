"""Cancellable background codec jobs; worker threads never access bpy."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass,field
from pathlib import Path
import copy,threading,time,uuid,os,tempfile
from . import formats

POOL=ThreadPoolExecutor(max_workers=2,thread_name_prefix='m2b-io')
JOBS={}
LOCK=threading.Lock()

@dataclass
class Job:
    id:str
    command:str
    path:str
    owner:int
    status:str='queued'
    created:float=field(default_factory=time.time)
    result:object=None
    error:str=''
    cancelled:threading.Event=field(default_factory=threading.Event)
    applied:bool=False
    revision:int|None=None
    def summary(self):
        return {'job_id':self.id,'command':self.command,'path':self.path,'status':self.status,'error':self.error,'created':self.created,'revision':self.revision,
                'result':self.result if isinstance(self.result,dict) else None}

def start(command,path,owner,grid=None):
    if command not in ('import_litematic','import_schem','export_litematic','export_schem'):raise ValueError('Unsupported IO command')
    path=str(Path(path).resolve())
    with LOCK:
        if any(j.path==path and j.status in ('queued','running') for j in JOBS.values()):raise ValueError('An active job already uses this path')
        job=Job(uuid.uuid4().hex,command,path,owner);JOBS[job.id]=job
    snapshot=None
    if grid is not None:
        snapshot=copy.copy(grid);snapshot.blocks=dict(grid.blocks);snapshot.regions=copy.deepcopy(grid.regions)
        job.revision=grid.revision
    def run():
        temp=None
        try:
            if job.cancelled.is_set():job.status='cancelled';return
            job.status='running'
            if command.startswith('import'):
                result=getattr(formats,command)(path)
                if job.cancelled.is_set():job.status='cancelled';return
                job.result=result;job.status='ready'
            else:
                target=Path(path);target.parent.mkdir(parents=True,exist_ok=True)
                fd,temp=tempfile.mkstemp(dir=target.parent,suffix=target.suffix);os.close(fd)
                result=getattr(formats,command)(snapshot,temp)
                with LOCK:
                    if job.cancelled.is_set():job.status='cancelled';return
                    os.replace(temp,path);temp=None
                    result['path']=path;job.result=result;job.status='completed'
        except Exception as exc:job.error=str(exc);job.status='failed'
        finally:
            if temp and os.path.exists(temp):os.unlink(temp)
    POOL.submit(run)
    return job.summary()

def cancel(job_id):
    with LOCK:
        job=JOBS[job_id]
        if job.status not in ('completed','failed','cancelled'):
            job.cancelled.set()
            if job.status=='ready':job.result=None;job.status='cancelled'
    return job.summary()

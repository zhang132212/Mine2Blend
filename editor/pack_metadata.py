"""Resource version ranges and overlays (Minecraft pack metadata, 25w31a+).

Specification: https://www.minecraft.net/en-us/article/minecraft-snapshot-25w31a
"""
from pathlib import PurePosixPath

TARGET=(88,0)

def version(value,upper=False):
    values=[value] if type(value) is int else value
    if not isinstance(values,list) or len(values) not in (1,2) or any(type(v) is not int or v<0 for v in values):raise ValueError('Invalid pack format version')
    return (values[0],values[1] if len(values)==2 else 2**31-1 if upper else 0)

def bounds(data,legacy='supported_formats'):
    if 'min_format' in data or 'max_format' in data:
        if not all(k in data for k in ('min_format','max_format')):raise ValueError('Both min_format and max_format are required')
        lo,hi=version(data['min_format']),version(data['max_format'],True)
    else:
        value=data.get(legacy,data.get('pack_format'))
        if type(value) is int:lo,hi=(value,0),(value,2**31-1)
        elif isinstance(value,list) and len(value)==2:lo,hi=version(value[0]),version(value[1],True)
        elif isinstance(value,dict):lo,hi=version(value['min_inclusive']),version(value['max_inclusive'],True)
        else:raise ValueError('Missing resource pack format')
    if lo>hi:raise ValueError('Pack minimum format exceeds maximum')
    return lo,hi

def resolve(names,metadata,target=TARGET):
    lo,hi=bounds(metadata.get('pack',{}))
    warnings=[] if lo<=target<=hi else [f'Pack declared range {lo}..{hi} excludes target {target}; preview compatibility is not guaranteed']
    resolved={name:name for name in names if name.startswith('assets/')}
    selected=[]
    for entry in metadata.get('overlays',{}).get('entries',[]):
        low,high=bounds(entry,'formats')
        directory=entry.get('directory','')
        if not directory or '\\' in directory or ':' in directory or PurePosixPath(directory).is_absolute() or '..' in PurePosixPath(directory).parts:raise ValueError('Unsafe overlay directory')
        if low<=target<=high:
            prefix=directory.rstrip('/')+'/'
            for name in names:
                if name.startswith(prefix+'assets/'):resolved[name[len(prefix):]]=name
            selected.append(directory)
    return resolved,selected,warnings

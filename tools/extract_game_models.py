"""Extract actual 26.2 baked layers using an installed client and Java 25.

No game launch, account authentication or world access is performed.
"""
from pathlib import Path
import argparse,json,os,subprocess

ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser();p.add_argument('--minecraft-dir',type=Path,required=True);p.add_argument('--java-home',type=Path,default=Path(os.environ['JAVA_HOME']) if os.environ.get('JAVA_HOME') else None)
    args=p.parse_args();base=args.minecraft_dir;version=base/'versions/26.2'
    base=base.resolve();version=base/'versions/26.2'
    if args.java_home is None:p.error('--java-home or JAVA_HOME is required')
    metadata=json.loads((version/'26.2.json').read_text(encoding='utf-8-sig'))
    artifacts=[base/'libraries'/lib['downloads']['artifact']['path'] for lib in metadata['libraries'] if 'artifact' in lib.get('downloads',{})]
    # Manifests also list native/platform libraries for other operating systems.
    artifacts=[path for path in artifacts if path.exists()]
    build=ROOT/'test-output/game-model-extractor';build.mkdir(parents=True,exist_ok=True)
    cp=os.pathsep.join(map(str,[version/'26.2.jar',*artifacts]));suffix='.exe' if os.name=='nt' else ''
    subprocess.run([str(args.java_home/'bin'/('javac'+suffix)),'-encoding','UTF-8','-cp',cp,'-d',str(build),str(ROOT/'tools/DumpGameModels.java')],check=True)
    target=ROOT/'editor/data/resources/vanilla-model-layers.json'
    result=subprocess.run([str(args.java_home/'bin'/('java'+suffix)),'-Djava.awt.headless=true','-cp',str(build)+os.pathsep+cp,'DumpGameModels',str(target)],cwd=build)
    if result.returncode:raise RuntimeError(f'Game model extractor failed ({result.returncode})')
    print(target)
    from build_vanilla_entities import build as bind_entities
    bind_entities()

if __name__=='__main__':main()

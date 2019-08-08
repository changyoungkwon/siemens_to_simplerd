from simplerd import ImageHeader
from twixreader import twixreader

def isnamedtupleinstance(x):
    _type = type(x)
    bases = _type.__bases__
    if len(bases) != 1 or bases[0] != tuple:
        return False
    fields = getattr(_type, '_fields', None)
    if not isinstance(fields, tuple):
        return False
    return all(type(i)==str for i in fields)

def unpack(obj):
    if isinstance(obj, dict):
        return {key: unpack(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [unpack(value) for value in obj]
    elif isnamedtupleinstance(obj):
        return {key: unpack(value) for key, value in obj._asdict().items()}
    elif isinstance(obj, tuple):
        return tuple(unpack(value) for value in obj)
    else:
        return obj

def main():
    from pathlib import Path
    import json
    files = Path('/mnt/file-server/PI_data/SNUH_backup').glob('???/**/*.dat')
    for i, filepath in enumerate(files):
        header_filename = 'test/{}_header.json'.format(str(filepath).split('/')[-1][:-4])
        try:
            twix = twixreader.read_twix(str(filepath))
            meas = twix.read_measurement(header_only=True)
            print(meas)
            if type(meas) is list:
                meas = meas[-1]
            print(meas)
            header = ImageHeader.convert(meas.hdr)
            with open(header_filename, 'w') as header_file:
                json.dump(unpack(header), header_file, indent=4)
        except Exception as ex:
            print('[error]file : {}\n message : {}\n'.format(str(filepath), ex))
            pass

if __name__ == '__main__':
    main()
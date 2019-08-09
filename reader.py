from simplerd import Image
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

def flatten_dict(obj, delim):
    """convert nested dict into simple dict"""
    flatten = {}
    for key, value in obj.items():
        if not isinstance(value, dict):
            flatten[key] = value
        else: 
            child = flatten_dict(value, delim)
            for k, v in child.items():
                flatten[''.join([key, delim, k])] = v
    return flatten



def main():
    from pathlib import Path
    import json
    from contextlib import redirect_stdout
    files = Path('/mnt/file-server/PI_data/SNUH_backup').glob('**/*.dat')
    files = list(files)
    print("[status]total number of files : {}".format(len(files)))
    dummy_text_file = open('dummy.txt', 'w')
    for i, filepath in enumerate(files):
        header_filename = 'test/{}_header.json'.format(str(filepath).split('/')[-1][:-4])
        try:
            with redirect_stdout(dummy_text_file):
                twix = twixreader.read_twix(str(filepath))
                measurements = twix.read_measurement(header_only=True)
            if not isinstance(measurements, list):
                measurements = [measurements]
            for meas in measurements:
                image = Image(meas.hdr, 0)
                image.header['filename'] = str(filepath)
                with open(header_filename, 'w') as header_file:
                    json.dump(image.header, header_file, indent=4)
            print("[status]{}/{} completed. work in progress".format(i, len(files)))
        except Exception as ex:
            print('[error]file : {}\n message : {}\n'.format(str(filepath), ex))
            pass
    dummy_text_file.close()


def json_to_csv():
    """Merge json files in the test folder into a single csv file"""
    from pathlib import Path
    import json
    import csv
    json_files = Path('test').glob('*.json')
    filename = 'parse_result.csv'
    with open(filename, 'w') as csv_file:
        writer = csv.writer(csv_file)
        keys_in_order = []
        for i, json_filepath in enumerate(json_files):
            with open(json_filepath, 'r') as json_file:
                data = json.load(json_file)
            flatten_data = flatten_dict(data, '/')
            if i == 0:
                keys_in_order = flatten_data.keys()
                writer.writerow(keys_in_order)
            values = [flatten_data[key] for key in keys_in_order]
            writer.writerow(values)

def debug():
    from pathlib import Path
    import json
    error_filenames = [
        '/mnt/file-server/PI_data/SNUH_backup/LSJ/raw data/meas_MID01037_FID22629_3D_ASL_24sl_5mm_PLD2300ms.dat',
        '/mnt/file-server/PI_data/SNUH_backup/LIH/raw data/meas_MID01207_FID22799_3D_ASL_24sl_5mm_PLD2300ms.dat',
    ]
    for filename in error_filenames:
        header_filename = 'test/{}_header_dict.json'.format(filename.split('/')[-1][:-4])
        twix = twixreader.read_twix(filename)
        meas = twix.read_measurement(header_only=True)
        if type(meas) is list:
            meas = meas[-1]
        meas.hdr.dump()
        image = Image(meas.hdr, 0)
        with open(header_filename, 'w') as header_file:
            json.dump(image.header, header_file, indent=4)

if __name__ == '__main__':
    main()
    json_to_csv()
    # debug()
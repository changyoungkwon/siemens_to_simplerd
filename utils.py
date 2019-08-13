from simplerd import Image
import csv
from twixreader import twixreader
import h5py
from pathlib import Path
import json
from contextlib import redirect_stdout

def _flatten_dict(obj, delim):
    """convert nested dict into simple dict"""
    flatten = {}
    for key, value in obj.items():
        if not isinstance(value, dict):
            flatten[key] = value
        else: 
            child = _flatten_dict(value, delim)
            for k, v in child.items():
                flatten[''.join([key, delim, k])] = v
    return flatten

def _expected_dimensions(header, as_dict=False):
    """return expected dimension from header"""
    expected_dimensions = header['encoding']['dimensions']
    expected_dimensions['channel'] = header['acquisition_system']['receiver_channels']
    expected_dimensions['readout'] = header['encoding']['encoded_space']['matrix_size'][0]
    # squeeze
    order = [
        'readout',
        'channel', 
        'kspace_encoding_step1',
        'kspace_encoding_step2',
        'slice',
        'repetition', 
        'set', 
        'segment',
        'contrast',
        'average', 
    ]
    if not as_dict:
        return [expected_dimensions[key] for key in order if expected_dimensions[key] != 1 ]
    else:
        return expected_dimensions

def save_header(filename):
    """save header of the dat file as json"""
    header_filename = 'headers/{}_header.json'.format(filename.split('/')[-1][:-4])
    try:
        twix = twixreader.read_twix(filename)
        for i in range(twix.num_meas):
            meas = twix.read_measurement(i, header_only=True)
            image = Image(meas.hdr, 0)
            image.header['expected_shape'] = _expected_dimensions(image.header)
            with open(header_filename, 'w') as f:
                json.dump(image.header, f)
    except Exception as ex:
        print("[error]file : {}\n message : {}".format(str(filepath), ex))

def save_mdh(filename):
    """print all mdh-index values, save as csv"""
    csv_filename = 'mdhs/{}_mdh.csv'.format(filename.split('/')[-1][:-4])
    twix = twixreader.read_twix(filename)
    for i in range(twix.num_meas):
        meas = twix.read_measurement(i)
        mdh_dim_order = meas.get_meas_buffer(0).mdh_dim_order
        mdh_all = meas._all_mdh
        print("[status]protocol name : {}".format(Image(meas.hdr, 0).header['measurement']['protocol_name']))
        print("[status]mdhs number : {}".format(len(mdh_all)))
        # write csv
        with open(csv_filename, 'w') as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames = mdh_dim_order)
            writer.writeheader()
            for i, mdh in enumerate(mdh_all):
                row = {}
                for k in mdh_dim_order:
                    row[k] = mdh[k]
                writer.writerow(row)
        print("Done")
        
def save_all(filename): 
    """save mdhs, and headers"""
    twix = twixreader.read_twix(filename)
    header_filename = 'headers/{}_header.json'.format(filename.split('/')[-1][:-4])
    csv_filename = 'mdhs/{}_mdh.csv'.format(filename.split('/')[-1][:-4])
    meas = twix.read_measurement(twix.num_meas - 1)
    # mdhs
    mdh_dim_order = meas.get_meas_buffer(0).mdh_dim_order
    mdh_all = meas._all_mdh
    print("[status]protocol name : {}".format(Image(meas.hdr, 0).header['measurement']['protocol_name']))
    print("[status]mdhs number : {}".format(len(mdh_all)))
    # write csv
    with open(csv_filename, 'w') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames = mdh_dim_order)
        writer.writeheader()
        for i, mdh in enumerate(mdh_all):
            row = {}
            for k in mdh_dim_order:
                row[k] = mdh[k]
            writer.writerow(row)
    # write header
    image = Image(meas.hdr, 0)
    image.header['expected_shape'] = _expected_dimensions(image.header)
    image.header['buffer/acquisition_number'] = len(meas._all_mdh) 
    image.header['buffer/readout'] = int(meas.get_meas_buffer(0).num_pixels)
    image.header['buffer/channels'] = int(meas.get_meas_buffer(0).num_channels)
    with open(header_filename, 'w') as f:
        json.dump(image.header, f, indent=4)

    print("mesurement {} done".format(meas.mid))


def json_to_csv(dirname):
    """Merge json files in the test folder into a single csv file"""
    # first read fieldnames
    samples = Path(dirname).glob('*.json')
    for json_filepath in samples:
        with open(json_filepath, 'r') as json_file:
            flatten_data = _flatten_dict(json.load(json_file), '/')
            fieldnames = flatten_data.keys()
        break
            
    json_files = Path(dirname).glob('*.json')
    filename = '{}_merge.csv'.format(dirname)
    with open(filename, 'w') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for i, json_filepath in enumerate(json_files):
            with open(json_filepath, 'r') as json_file:
                data = json.load(json_file)
            flatten_data = _flatten_dict(data, '/')
            writer.writerow(flatten_data)

def get_image(filename):
    twix = twixreader.read_twix(filename)
    measurements = twix.read_measurement()
    if not isinstance(measurements, list):
        measurements = [measurements]
    for meas in measurements:
        data = meas.get_meas_buffer(0)[...]
        print('image dimension : {}'.format(data.shape))
        with h5py.File('output.h5', 'w') as output_file:
            dataset_name = 'data_{}'.format(meas.mid)
            output_file.create_dataset(dataset_name, data.shape, data.dtype, data)

if __name__ == '__main__':
    # get_image('/mnt/file-server/PI_data/SNUH_backup/190629/LEE_SANG_IN/meas_MID00425_FID13889_POST_COR_T1_TSE.dat')
    # debug("/mnt/file-server/PI_data/SNUH_backup/190705/LEE SEUNG HO/meas_MID02056_FID19444_AX_T2_TSE.dat")
    # main('/mnt/file-server/PI_data/SNUH_backup/190705/LEE SEUNG HO/meas_MID02056_FID19444_AX_T2_TSE.dat')
    # json_to_csv()
    # compare_dimension()
    files_tse = Path('/mnt/file-server/PI_data/SNUH_backup').glob('**/*T2_TSE*.dat')
    files_flair = Path('/mnt/file-server/PI_data/SNUH_backup').glob('**/*T2_FLAIR*.dat')
    for filename in files_tse:
        try: 
            save_all(filename)
            print("[status]successfully save {}'s".format(filename))
        except Exception as ex:
            print("[error]error {}\nmessage {}".format(filename, ex))

    for filename in files_flair:
        try: 
            save_all(filename)
            print("[status]successfully save {}'s".format(filename))
        except Exception as ex:
            print("[error]error {}\nmessage {}".format(filename, ex))

    json_to_csv('headers')

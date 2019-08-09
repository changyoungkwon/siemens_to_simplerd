class Image:
    def __init__(self, siemens_header, buffer):
        dicom = siemens_header['Dicom']['xprot']['']['DICOM']
        yaps = siemens_header['Meas']['xprot']['']['YAPS']
        meas = siemens_header['Meas']['xprot']['']['MEAS']
        header = siemens_header['Meas']['xprot']['']['HEADER']
        iris = siemens_header['Meas']['xprot']['']['IRIS']

        #encoding
        phaseOverSampling = iris['DERIVED'].get('phaseOverSampling', 0)
        trajectory = {
            1: 'cartesian',
            2: 'radial',
            4: 'spiral', 
            8: 'propeller', 
        }.get(meas['sKSpace']['ucTrajectory'][0], 'other')
        phaseResolution = meas['sKSpace']['dPhaseResolution']

        if 0 in meas['sSliceArray']['asSlice'].keys():
            sliceData = meas['sSliceArray']['asSlice'][0]
        else:
            sliceData = siemens_header['MeasYaps']['ascconv']['sSliceArray']['asSlice'][0]
        if trajectory == 'cartesian':
            encodedSpaceX = yaps['iNoOfFourierColumns']
        else:
            encodedSpaceX = iris['DERIVED']['imageColumns']

        if meas['sKSpace'].get('uc2DInterpolation', -1) == 1:
            encodedSpaceY = yaps['iPEFTLength'] / 2
        else:
            encodedSpaceY = yaps['iPEFTLength']

        if 'iNoOfFourierPartitions' not in yaps.keys() or yaps['i3DFTLength'] == 1:
            encodedSpaceZ = 1
        else:
            encodedSpaceZ = yaps['i3DFTLength']

        # encoding-dimension
        if 'ucSegmentationMode' in meas['sFastImaging'].keys():
            segments_candidate = yaps['iNoOfFourierPartitions'] * yaps['iNoOfFourierLines'] / meas['sFastImaging']['lSegements'] if meas['sFastImaging'].get('lSegments')[0] > 1 else 1
            segment = {
                1: segments_candidate,
                2: meas['sFastImaging'].get('lShots', 1),
            }.get(meas['sFastImaging']['ucSegmentationMode'][0], 1)
        else:
            segment = 1


        self.header = {
            "acquisition_system": {
                "institution_name"      : dicom['InstitutionName'],
                "receiver_channels"     : yaps['iMaxNoOfRxChannels'],
                "system_field_strength" : yaps['flMagneticFieldStrength'],
                "system_vendor"         : dicom['Manufacturer'],
                "system_model"          : dicom['ManufacturersModelName'],
            },
            "measurement": {
                "scan_date"         : yaps['tFrameOfReference'][0].split('.')[10][:8],
                "acquisition_type"  : dicom['tMRAcquisitionType'],
                "measurement_uid"   : header['MeasUID'],
                "protocol_name"     : meas['tProtocolName'],
            },
            "encoding": {
                "trajectory": trajectory,
                "encoded_space": {
                    "matrix_size": (encodedSpaceX, encodedSpaceY, encodedSpaceZ),
                    "field_of_view": (
                        sliceData['dReadoutFOV'] * yaps['flReadoutOSFactor'][0],
                        sliceData['dPhaseFOV'] * (1 + phaseOverSampling),
                        sliceData['dThickness'] * (1 + phaseOverSampling),
                    ),
                },
                "recon_space": {
                    "matrix_size": (
                        iris['DERIVED']['ImageColumns'],
                        iris['DERIVED']['ImageLines'],
                        1 if yaps['i3DFTLength'] == 1 else meas['sKSpace']['lImagesPerSlab'],
                    ),
                    "field_of_view": (
                        sliceData['dReadoutFOV'],
                        sliceData['dPhaseFOV'],
                        sliceData['dThickness'],
                    ),
                },
                "dimensions": {
                    "kspace_encoding_step1": yaps['iNoOfFourierLines'],
                    "kspace_encoding_step2": yaps.get('iNoOfFourierPartitions', 1) if yaps['i3DFTLength'] != 1 else 1,
                    "average"              : meas.get('lAverages', 1),
                    "contrast"             : meas.get('lContrasts', 1),
                    "phase"                : meas['sPhysioImaging'].get('lPhases', 1),
                    "repetition"           : meas.get('lRepetitions', 1),
                    "segment"              : segment,
                    "set"                  : yaps.get('iNSet', 1),
                    "slice"                : meas['sSliceArray'].get('lSize', 1),
                },
                "phase_resolution": meas['sKSpace']['dPhaseResolution']
            },
            "parallel_imaging": {
                "acceleration_factor": {
                    "kspace_encoding_step_1": meas.get('sPat', {}).get('lAccelFactPE', 1),
                    "kspace_encoding_step_2": meas.get('sPat', {}).get('lAccelFact3D', 1),
                },
                "first_acs_line": yaps.get('lFirstRefLine', -1),
                "n_acs_lines"   : meas.get('sPat', {}).get('lRefLinesPE', 0),
            },
            "sequence_parameters": {
                "turbo_factor"     : meas.get('sFastImaging', {}).get('lSliceTurboFactor', 1),
                "TE"               : [ te / 1000.0 for te in meas['alTE'] if te > 0 ],
                "TR"               : [ tr / 1000.0 for tr in meas['alTR'] if tr > 0 ],
                "TI"               : [ ti / 1000.0 for ti in meas['alTI'] if ti > 0 ],
                "flip_angle_degree": [ angle for angle in dicom['adFlipAngleDegree'] if angle > 0 ],
            },
        }

        self.buffer = buffer

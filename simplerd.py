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
            encodedSpaceX = yaps['iNoOfFourierColumns'][0]
        else:
            encodedSpaceX = iris['DERIVED']['ImageColumns'][0]

        if meas['sKSpace'].get('uc2DInterpolation', -1) == 1:
            encodedSpaceY = yaps['iPEFTLength'][0] / 2
        else:
            encodedSpaceY = yaps['iPEFTLength'][0]

        if 'iNoOfFourierPartitions' not in yaps.keys() or yaps['i3DFTLength'] == 1:
            encodedSpaceZ = 1
        else:
            encodedSpaceZ = yaps['i3DFTLength'][0]

        # encoding-dimension
        if 'ucSegmentationMode' in meas['sFastImaging'].keys():
            segments_candidate = yaps['iNoOfFourierPartitions'][0] * yaps['iNoOfFourierLines'][0] / meas['sFastImaging']['lSegments'][0] if meas['sFastImaging'].get('lSegments')[0] > 1 else 1
            segment = {
                1: segments_candidate,
                2: meas['sFastImaging'].get('lShots', [1])[0],
            }.get(meas['sFastImaging']['ucSegmentationMode'][0], 1)
        else:
            segment = 1


        self.header = {
            "acquisition_system": {
                "institution_name"      : dicom['InstitutionName'][0],
                "receiver_channels"     : yaps['iMaxNoOfRxChannels'][0],
                "system_field_strength" : yaps['flMagneticFieldStrength'][0],
                "system_vendor"         : dicom['Manufacturer'][0],
                "system_model"          : dicom['ManufacturersModelName'][0],
            },
            "measurement": {
                "scan_date"         : yaps['tFrameOfReference'][0].split('.')[10][:8],
                "acquisition_type"  : dicom['tMRAcquisitionType'][0],
                "measurement_uid"   : header['MeasUID'][0],
                "protocol_name"     : meas['tProtocolName'][0],
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
                        iris['DERIVED']['ImageColumns'][0],
                        iris['DERIVED']['ImageLines'][0],
                        1 if yaps['i3DFTLength'][0] == 1 else meas['sKSpace']['lImagesPerSlab'][0],
                    ),
                    "field_of_view": (
                        sliceData['dReadoutFOV'],
                        sliceData['dPhaseFOV'],
                        sliceData['dThickness'],
                    ),
                },
                "dimensions": {
                    "kspace_encoding_step1": 1 if len(yaps['iNoOfFourierLines']) == 0 else yaps['iNoOfFourierLines'][0],
                    "kspace_encoding_step2": 1 if yaps['i3DFTLength'][0] != 1 and len(yaps['iNoOfFourierPartitions']) == 0 else yaps['iNoOfFourierPartitions'][0],
                    "slice"                : meas['sSliceArray']['lSize'][0],
                    "phase"                : meas['sPhysioImaging']['lPhases'][0],
                    "repetition"           : 1 if len(meas['lRepetitions']) == 0 else meas['lRepetitions'][0],
                    "set"                  : yaps['iNSet'][0],
                    "segment"              : segment,
                    "contrast"             : meas['lContrasts'][0],
                    "average"              : meas['lAverages'][0],
                },
                "phase_resolution": meas['sKSpace']['dPhaseResolution'][0],
            },
            "parallel_imaging": {
                "acceleration_factor": {
                    "kspace_encoding_step1": 1 if len(meas['sPat']['lAccelFactPE']) == 0 else meas['sPat']['lAccelFactPE'][0],
                    "kspace_encoding_step2": 1 if len(meas['sPat']['lAccelFact3D']) == 0 else meas['sPat']['lAccelFact3D'][0],
                },
                "first_acs_line": {
                    "kspace_encoding_step1": yaps['lFirstRefLine'][0],
                    "kspace_encoding_step2": yaps['lFirstRefPartition'][0],
                },
                "n_acs_lines"   : {
                    "kspace_encoding_step1": 0 if len(meas['sPat']['lRefLinesPE']) == 0 else meas['sPat']['lRefLinesPE'][0],
                    "kspace_encoding_step2": 0 if len(meas['sPat']['lRefLines3D']) == 0 else meas['sPat']['lRefLines3D'][0],
                }, 
            },
            "sequence_parameters": {
                "turbo_factor"     : meas['sFastImaging']['lTurboFactor'][0],
                "TR"               : [ tr / 1000.0 for i, tr in enumerate(meas['alTR']) if i == 0 or tr > 0 ],
                "TE"               : [ te / 1000.0 for i, te in enumerate(meas['alTE']) if i == 0 or (te > 0 and 0 < i < meas['lContrasts'][0])],
                "TI"               : [ ti / 1000.0 for ti in meas['alTI'] if ti > 0 ],
                "flip_angle_degree": [ angle for angle in dicom['adFlipAngleDegree'] if angle > 0 ],
            },
        }

        self.buffer = buffer

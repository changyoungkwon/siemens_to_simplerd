from typing import NamedTuple, Tuple

class _Space(NamedTuple):
    matrixSize: Tuple[int, int, int]
    fieldOfView: Tuple[float, float, float]

class _Dimension(NamedTuple):
    kspaceEncodingStep1: int
    kspaceEncodingStep2: int
    average: int
    slice: int
    contrast: int
    phase: int
    repetition: int
    set: int
    segment: int

class _AcquisitionSystem(NamedTuple):
    systemVendor: str
    systemModel: str
    systemFieldStrength: float
    receiverChannels: int
    institutionName: str

class _Measurement(NamedTuple):
    date: str
    measurementUid: str
    protocolName: str
    acquisitionType: str

class _Encoding(NamedTuple):
    trajectory: str
    encodedSpace: _Space
    reconSpace: _Space
    dimension: _Dimension 
    phaseResolution: float

class _AccelerationFactor(NamedTuple):
    kspaceEncodingStep1: int
    kspaceEncodingStep2: int

class _ParallelImaging(NamedTuple):
    accelerationFactor: _AccelerationFactor
    firstAcsLine: int
    nAcsLines: int

class _SequenceParameters(NamedTuple):
    TR: float
    TE: float
    TI: float
    flipAngleDegree: float
    turboFactor: int


class ImageHeader(NamedTuple):
    acquisitionSystem: _AcquisitionSystem
    measurement: _Measurement
    encoding: _Encoding
    parallelImaging: _ParallelImaging
    sequenceParameters: _SequenceParameters

    @classmethod
    def convert(cls, siemens_header):
        dicom = siemens_header['Dicom']['xprot']['']['DICOM']
        yaps = siemens_header['Meas']['xprot']['']['YAPS']
        meas = siemens_header['Meas']['xprot']['']['MEAS']
        header = siemens_header['Meas']['xprot']['']['HEADER']
        iris = siemens_header['Meas']['xprot']['']['IRIS']

        # acquisitionSystem
        acquisitionSystem = _AcquisitionSystem(
            institutionName = dicom['InstitutionName'],
            receiverChannels = yaps['iMaxNoOfRxChannels'],
            systemFieldStrength = yaps['flMagneticFieldStrength'],
            systemVendor = dicom['Manufacturer'],
            systemModel = dicom['ManufacturersModelName'],
        )

        # measurement
        measurement = _Measurement(
            date = yaps['tFrameOfReference'][0].split('.')[10][:8],
            acquisitionType = dicom['tMRAcquisitionType'],
            measurementUid = header['MeasUID'],
            protocolName = meas['tProtocolName'],
        )

        #encoding
        phaseOverSampling = iris['DERIVED'].get('phaseOverSampling', 0)

        trajectory = {
            1: 'cartesian',
            2: 'radial',
            4: 'spiral', 
            8: 'propeller', 
        }.get(meas['sKSpace']['ucTrajectory'][0], 'other')
        phaseResolution = meas['sKSpace']['dPhaseResolution']

        if '0' in meas['sSliceArray']['asSlice'].keys():
            sliceData = meas['sSliceArray']['asSlice']['0']
        else:
            sliceData = siemens_header['MeasYaps']['ascconv']['sSliceArray']['asSlice']['0']
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

        encodedSpace = _Space(
            matrixSize = (
                encodedSpaceX,
                encodedSpaceY,
                encodedSpaceZ,
            ),
            fieldOfView = (
                sliceData['dReadoutFOV'] * yaps['flReadoutOSFactor'][0],
                sliceData['dReadoutFOV'] * (1 + phaseOverSampling),
                sliceData['dThickness'] * (1 + phaseOverSampling)
            ),
        )


        reconSpace = _Space(
            matrixSize = (
                iris['DERIVED']['ImageColumns'],
                iris['DERIVED']['ImageLines'],
                1 if yaps['i3DFTLength'] == 1 else meas['sKSpace']['lImagesPerSlab'],
            ),
            fieldOfView = (
                sliceData['dReadoutFOV'],
                sliceData['dReadoutFOV'],
                sliceData['dThickness'],
            )
        )
        # encoding-dimension
        if 'ucSegmentationMode' in meas['sFastImaging'].keys():
            segments_candidate = yaps['iNoOfFourierPartitions'] * yaps['iNoOfFourierLines'] / meas['sFastImaging']['lSegements'] if meas['sFastImaging'].get('lSegments')[0] > 1 else 1
            segment = {
                1: segments_candidate,
                2: meas['sFastImaging'].get('lShots', 1),
            }.get(meas['sFastImaging']['ucSegmentationMode'][0], 1)
        else:
            segment = 1

        dimension = _Dimension(
            kspaceEncodingStep1 = yaps['iNoOfFourierLines'],
            kspaceEncodingStep2 = yaps.get('iNoOfFourierPartitions', 1) if yaps['i3DFTLength'] != 1 else 1,
            average = meas.get('lAverages', 1),
            contrast = meas.get('lContrasts', 1),
            phase = meas['sPhysioImaging'].get('lPhases', 1),
            repetition = meas.get('lRepetitions', 1),
            segment = segment,
            set = yaps.get('iNSet', 1),
            slice = meas.get('lSize', 1),
        )
        encoding = _Encoding(
            trajectory = trajectory,
            encodedSpace = encodedSpace,
            reconSpace = reconSpace,
            dimension = dimension,
            phaseResolution = phaseResolution,
        )

        # parallelImaging
        parallelImaging = _ParallelImaging(
            accelerationFactor = _AccelerationFactor(
                meas.get('sPat', {}).get('lAccelFactPE', 1),
                meas.get('sPat', {}).get('lAccelFact3D', 1),
            ),
            firstAcsLine = yaps.get('lFirstRefLine', -1),
            nAcsLines = meas.get('sPat', {}).get('lRefLinesPE', 0),
        )

        # sequenceParameters
        sequenceParameters = _SequenceParameters(
            turboFactor = meas.get('sFastImaging', {}).get('lSliceTurboFactor', 1),
            TE = [ te / 1000.0 for te in meas['alTE'] if te > 0 ],
            TR = [ tr / 1000.0 for tr in meas['alTR'] if tr > 0 ],
            TI = [ ti / 1000.0 for ti in meas['alTI'] if ti > 0 ],
            flipAngleDegree = [ angle for angle in dicom['adFlipAngleDegree'] if angle > 0 ],
        )

        return cls( 
            acquisitionSystem=acquisitionSystem, 
            measurement=measurement, 
            encoding=encoding, 
            parallelImaging=parallelImaging, 
            sequenceParameters=sequenceParameters 
        )

    @property
    def dimension(self):
        """return full dimension(COL X CHA X LIN X ...)"""

    @property
    def shape(self):
        """return only shape of image(COL X CHA X LIN X SLC)""" 

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

if __name__ == '__main__':
    import json
    with open('MID00832_header.json', 'r') as header_file:
        siemens_header = json.load(header_file)
    simple_header = ImageHeader.convert(siemens_header)
    header = simple_header._asdict()
    with open('dum_header.json', 'w') as header_file:
        json.dump(unpack(simple_header), header_file, indent=4)
from typing import NamedTuple

class _Space(NamedTuple):
    matrixSize: NamedTuple('_MatrixSize', [('x', int), ('y', int), ('z', int)])
    fieldOfView: NamedTuple('_fieldOfView', [('x', float), ('y', float), ('z', float)])

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

class _ParallelImaging(NamedTuple):
    accelerationFactor: NamedTuple('_AccelerationFactor', [('kspaceEncodingStep1', int), ('kspaceEncodingStep2', int)])
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

    def read(self, siemens_header):
        dicom = simple_header['Dicom']['xprot']['']['DICOM']
        yaps = simple_header['Meas']['xprot']['']['YAPS']
        meas = simple_header['Meas']['xprot']['']['MEAS']
        header = simple_header['Meas']['xprot']['']['HEADER']

        self.acquisitionSystem.institutionName = dicom['InstitutionName']
        self.acquisitionSystem.receiverChannels = yaps['iMaxNoOfRxChannels']
        self.acquisitionSystem.systemFieldStrength = yaps['flMagneticFieldStrength']
        self.acquisitionSystem.systemVendor = dicom['Manufacturer']
        self.acquisitionSystem.systemModel = dicom['ManufacturersModelName']
        
        self.measurement.acquisitionType = dicom['tMRAcquisitionType']
        self.measurement.measurementUid = header['MeasUID']
        self.measurement.protocolName = meas['tProtocolName']

        self.encoding.phaseResolution = meas['sKSpace']['dPhaseResolution']
        self.encoding.trajectory = {
            1: 'cartesian',
            2: 'radial',
            4: 'spiral', 
            8: 'propeller', 
        }.get(meas['sKSpace']['ucTrajectory'], 'other')
        self.encoding.encodedSpace = _Space(_MatrixSize(), _FieldOfView())  # TODO
        self.encoding.reconSpace = _Space(_MatrixSize(), _FieldOfVIew())    # TODO
        self.encoding.dimension.kspaceEncodingStep1 = yaps['iNoOfFourierLines']
        self.encoding.dimension.kspaceEncodingStep2 = yaps.get('iNoOfFourierPartitions', 1) if yaps['i3DFTLength'] != 1 else 1
        self.encoding.dimension.average = meas.get('lAverages', 1)
        self.encoding.dimension.contrast = meas.get('lContrasts', 1)
        self.encoding.dimension.phase = meas['sPhysioImaginig'].get('lPhases', 1)
        self.encoding.dimension.repetition = meas.get('lRepetitions', 1)

        if 'ucSegmentationMode' in meas['sFastImaging'].keys():
            segments_candidate = yaps['iNoOfFourierPartitions'] * yaps['iNoOfFourierLines'] / meas['sFastImaging']['lSegements'] if meas['sFastImaging'].get('lSegments') > 1 else 1
            segment = {
                1: segments_candidate
                2: meas['sFastImaging'].get('lShots', 1)
            }.get(meas['sFastImaging']['ucSegmentationMode'], 1)
        else :
            segment = 1
        self.encoding.dimension.segment = segment
        self.encoding.dimension.set = yaps.get('iNset', 1)
        self.encoding.dimension.slice = meas.get('lSize', 1)
        
        self.parallelImaging.accelerationFactor.kspaceEncodingStep1 = meas.get('sPat', {}).get('lAccelFactPE', 1)
        self.parallelImaging.accelerationFactor.kspaceEncodingStep2 = meas.get('sPat', {}).get('lAccelFact3D', 1)
        self.parallelImaging.firstAcsLine = yaps.get('lFirstRefLine', -1)
        self.parallelImaging.nAcsLines = meas.get('sPat', {}).get('lRefLinesPE', 0)

        self.sequneceParameters.turboFactor = meas.get('sFastImaging', {}).get('lSliceTurboFactor', 1)
        self.sequenceParameters.TE = [ te / 1000.0 for te in meas['alTE'] if te > 0 ]
        self.sequenceParameters.TR = [ tr / 1000.0 for tr in meas['alTR'] if tr > 0 ]
        self.sequenceParameters.TI = [ ti / 1000.0 for ti in meas['alTI'] if ti > 0 ]
        self.sequenceParameters.flipAngleDegree = [ angle for angle in dicom['adFlipAngleDegree'] if angle > 0 ]

    @property
    def dimension(self):
        """return full dimension"""

    @property
    def shape(self):
        """return only shape of image""" 

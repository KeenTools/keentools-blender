from ..blender_independent_packages.pykeentools_loader import module as pkt_module


class GTClassLoader:
    @staticmethod
    def GTCameraInput_class():
        from .camera_input import GTCameraInput
        return GTCameraInput

    @staticmethod
    def GTGeoInput_class():
        from .camera_input import GTGeoInput
        return GTGeoInput

    @staticmethod
    def GTImageInput_class():
        from .camera_input import GTImageInput
        return GTImageInput

    @staticmethod
    def GTMask2DInput_class():
        from .camera_input import GTMask2DInput
        return GTMask2DInput

    @staticmethod
    def GeoTracker_class():
        return pkt_module().GeoTracker

    @staticmethod
    def PrecalcRunner_class():
        from .utils.precalc_runner import PrecalcRunner
        return PrecalcRunner

    @staticmethod
    def CalculationClient_class():
        from .utils.calculation_client import CalculationClient
        return CalculationClient

    @staticmethod
    def precalc():
        return pkt_module().precalc

    @staticmethod
    def TRProgressCallBack_class():
        from .utils.progress_callbacks import TRProgressCallBack
        return TRProgressCallBack

    @staticmethod
    def RFProgressCallBack_class():
        from .utils.progress_callbacks import RFProgressCallBack
        return RFProgressCallBack

    @staticmethod
    def DetectionProgressCallback_class():
        from .utils.progress_callbacks import DetectionProgressCallback
        return DetectionProgressCallback

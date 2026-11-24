import cv2
from core.logger import logger




class Camera:
    def __init__(self, index: int = 0):
        self._index = index
        self._camera = None

    def open(self) -> bool:

        if self._camera is not None and self._camera.isOpened():
            logger.warning("Trying to open an already opened camera")
            return True
        
        cam = cv2.VideoCapture(self._index)
        
        if not cam.isOpened():
            logger.error(f"Failed to open camera at index {self._index}")

            cam.release()
            self._camera = None

            return False

        self._camera = cam

        logger.info("Camera open successfully")

        return True


    def close(self) -> bool:
        if self._camera is None:
            logger.error("Trying to close camera when it wasn't opened yet")
            return False


        self._camera.release()
        self._camera = None

        cv2.destroyAllWindows()

        logger.info("Camera closed successfully")

        return True

    def show(self) -> None:
        logger.info("Press q to exit")
        
        while True:
            ret, frame = self._camera.read()
            if not ret:
                break
            
            cv2.imshow("Webcam Feed", frame)

            # Wait 1 ms and exit if 'q' is pressed
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break


camera = Camera()



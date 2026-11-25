from core.logger import logger
from core import constants
from vision.camera import camera

import sys





def main() -> int:
    exitCode = constants.exit_status.SUCCESS


    # initialize the logger sub-system
    if not logger.initialize("resources/logs/app.log"):
        print("Logging sub-system failed to initialized!")
        return constants.exit_status.FAILURE



    logger.info("WELCOME to AI powered Smart Attendence System")


    try:
        if not camera.open():
            exitCode = constants.exit_status.FAILURE
            return exitCode
        

        camera.show()


    except Exception:
        logger.error("Unexpected error occurred")
        exitCode = constants.exit_status.FAILURE
        raise Exception


    finally:
        try:
            # Initialize camera vision
            if not camera.close():
                exitCode = constants.exit_status.FAILURE


        finally:
            logger.shutdown()



    return exitCode





from deepface import DeepFace
import json


def get_reference_embedding(image_path: str, detector_backend: str = "opencv"):
    # Load a clear photo of the known person and extract their 512-D vector once
    results = DeepFace.represent(
        img_path=image_path,
        model_name="Facenet512",
        detector_backend=detector_backend,
        enforce_detection=True,
        align=True,
    )
    return results[0]["embedding"]  # list of 512 floats

if __name__ == "__main__":
    # data = {
    #     "shaury": get_reference_embedding("resources/assets/shaury.jpg"),
    #     "aditya": get_reference_embedding("resources/assets/aditya.jpg"),
    # }
    # with open("resources/data/mock.json", "w", encoding="utf-8") as file:
    #     json.dump(data, file, indent=2)

    
    sys.exit(main())





#include "logger.h"



int main(void)
{
    logger_metadata_obj meta = {0};
    
    meta.app.name = "test";

    if (!logger_init("logs/application.log", LOG_LEVEL_TRACE, &meta))
        return 1;

    LOG_TRACE("Application trace");
    LOG_DEBUG("Debugging renderer initialization");
    LOG_INFO("Application started successfully");

    LOG_WARNING("Window is not focused");


    LOG_FATAL("Critical application failure");
    LOG_ERROR("Failed to load texture: %s", "image.png");

    // logger_flush();

    logger_shutdown();

    return 0;
}



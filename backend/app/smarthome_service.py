import logging
import tinytuya
from typing import Dict, Any

logger = logging.getLogger("arya.smarthome")

TUYA_DEVICE_ID = "10721751d8f15b839464"
TUYA_IP = "192.168.31.19"
TUYA_LOCAL_KEY = "1VF4pcuqe/IP6=18"
TUYA_VERSION = 3.3

class SmarthomeService:
    def __init__(self):
        self.bulb = None
        self._init_device()

    def _init_device(self):
        try:
            self.bulb = tinytuya.BulbDevice(
                dev_id=TUYA_DEVICE_ID,
                address=TUYA_IP,
                local_key=TUYA_LOCAL_KEY,
                version=TUYA_VERSION
            )
            logger.info("Successfully initialized Wipro Smart Bulb via tinytuya.")
        except Exception as e:
            logger.error(f"Failed to initialize Wipro Smart Bulb: {e}")

    def turn_on_lights(self) -> Dict[str, Any]:
        if not self.bulb:
            return {"success": False, "message": "Bulb is not initialized."}
        try:
            self.bulb.turn_on()
            return {"success": True, "message": "Room lights are now turned ON."}
        except Exception as e:
            return {"success": False, "message": f"Failed to turn on lights: {e}"}

    def turn_off_lights(self) -> Dict[str, Any]:
        if not self.bulb:
            return {"success": False, "message": "Bulb is not initialized."}
        try:
            self.bulb.turn_off()
            return {"success": True, "message": "Room lights are now turned OFF."}
        except Exception as e:
            return {"success": False, "message": f"Failed to turn off lights: {e}"}

smarthome_service = SmarthomeService()

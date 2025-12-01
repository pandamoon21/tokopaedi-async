import random
import uuid
import json
import base64
def randomize_fp():
    user_id = [
        "223400020", "223400013", "223400069", "223400121", "223400127",
        "223400155", "223400222", "223400306", "223400283", "223400333",
        "223400375", "223400401", "223400518", "223400645", "223400790",
        "223400813", "223400873", "223400897", "223400963", "223401040",
        "223401175", "223401183", "223401452", "223401492", "223401493",
        "223401538", "223401665", "223401754", "223401902", "223401916",
        "223401917", "223401930", "223401947", "223401978", "223402015",
        "223402029", "223402064", "223402123", "223402191", "223402301",
        "223402349", "223402559", "223402574", "223402628", "223402629",
        "223402704", "223402725", "223402769", "223403073", "223403136",
        "223403203", "223403259", "223403265", "223403307", "223403378",
        "223403449", "223403480", "223403556", "223403607", "223403658",
        "223403693", "223403697", "223403724", "223403781", "223403814",
        "223403968", "223403994", "223404084", "223404155", "223404217",
        "223404226", "223404296", "223404394", "223404413", "223404427",
        "223404433", "223404477", "223404522", "223404617", "223404632",
        "223404679", "223404815", "223404840", "223404898", "223404906",
        "223405003", "223405034", "223405188", "223405199", "223405266",
        "223405302", "223405343", "223405359"
    ]
    iphone_models = [
        "iPhone SE", "iPhone 11", "iPhone 12", "iPhone 12 Mini",
        "iPhone 13", "iPhone 13 Pro Max",
        "iPhone 14", "iPhone 14 Pro", 
        "iPhone 15", "iPhone 15 Pro Max",
        "iPhone 16", "iPhone 16 Pro",
        "iPhone 17", "iPhone 17 Pro Max"
    ]
    ios_versions = [
        "14.8", "15.7", "16.6", "17.0", "17.5", "18.0", "18.2", "18.5", "19.1"
    ]
    screen_resolutions = [
        "1334x750",   # SE (3rd Gen)
        "1792x828",   # iPhone 11 / XR
        "2340x1080",  # iPhone 12/13 Mini
        "2532x1170",  # iPhone 12/13/14
        "2556x1179",  # iPhone 14/15/16 Pro
        "2778x1284",  # iPhone 12/13/14 Pro Max & Plus models
        "2796x1290"   # iPhone 14/15/16/17 Pro Max
    ]
    user_agents = [
        # iOS 14.8
        "Mozilla/5.0 (iPhone; CPU iPhone OS 14_8 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Mobile/15E148 Safari/604.1",
        # iOS 15.7
        "Mozilla/5.0 (iPhone; CPU iPhone OS 15_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.6 Mobile/15E148 Safari/604.1",
        # iOS 16.6
        "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
        # iOS 17.5
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1",
        # iOS 18.2
        "Mozilla/5.0 (iPhone; CPU iPhone OS 18_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Mobile/15E148 Safari/604.1",
        # iOS 19.1
        "Mozilla/5.0 (iPhone; CPU iPhone OS 19_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/19.1 Mobile/15E148 Safari/604.1"
    ]

    # Java Island bounds only
    longitudes = (104.5, 114.0)
    latitudes = (-8.8, -5.5)


    ios_version = random.choice(ios_versions)

    fingerprint = {
        "device_manufacturer": "Apple",
        "timezone": "Asia/Jakarta",
        "location_longitude": str(random.uniform(*longitudes)),
        "location_latitude": str(random.uniform(*latitudes)),
        "idfa": str(uuid.uuid4()).upper(),
        "is_emulator": False,
        "unique_id": str(uuid.uuid4()).upper(),
        "access_type": 1,
        "device_system": "iOS",
        "device_model": "iPhone",
        "is_tablet": False,
        "user_agent": random.choice(user_agents),
        "is_jailbroken_rooted": False,
        "screen_resolution": random.choice(screen_resolutions),
        "versionName": f"2.{random.randint(300, 350)}.{random.randint(0, 9)}",
        "current_os": ios_version,
        "language": "id",
        "device_name": random.choice(iphone_models)
    }

    json_str = json.dumps(fingerprint)
    b64_str = base64.b64encode(json_str.encode("utf-8")).decode("utf-8")

    return random.choice(user_id), b64_str
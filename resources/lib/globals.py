class GlobalVariables:
    VIDEO_PLAYING = 'VIDEO_PLAYING'
    VIDEO_ID = 'VIDEO_ID'

    ZIGGO_URL = 'https://www.ziggogo.tv/'
    ZIGGOPROD_URL = 'https://prod.spark.ziggogo.tv/'
    STATIC_URL = 'https://staticqbr-nl-prod.prod.cdn.dmdsdp.com/'
    authentication_URL = ZIGGOPROD_URL + 'auth-service/v1/authorization'
    personalisation_URL = ZIGGOPROD_URL + 'eng/web/personalization-service/v1/customer/{householdid}'
    entitlements_URL = ZIGGOPROD_URL + 'eng/web/purchase-service/v2/customers/{householdid}/entitlements'
    widevine_URL = ZIGGOPROD_URL + 'eng/web/session-manager/license/certificate/widevine'
    license_URL = ZIGGOPROD_URL + 'eng/web/session-manager/license'
    channels_URL = ZIGGOPROD_URL + 'eng/web/linear-service/v2/channels'
    streaming_URL = ZIGGOPROD_URL + 'eng/web/session-service/session/v2/web-desktop/customers/{householdid}'
    # /8654807_nl/vod?contentId='
    homeservice_URL = ZIGGOPROD_URL + 'eng/web/personal-home-service/'
    vod_service_URL = ZIGGOPROD_URL + 'eng/web/vod-service/v3/'
    linearservice_v2_URL = ZIGGOPROD_URL + 'eng/web/linear-service/v2/'
    linearservice_v1_URL = ZIGGOPROD_URL + 'eng/web/linear-service/v1/'
    pickerservice_URL = ZIGGOPROD_URL + 'eng/web/picker-service/v1/'

    SESSION_INFO = 'session.json'
    CUSTOMER_INFO = 'customer.json'
    CHANNEL_INFO = 'channels.json'
    ENTITLEMENTS_INFO = 'entitlements.json'
    WIDEVINE_LICENSE = 'widevine.json'
    COOKIES_INFO = 'cookies.json'

    CONST_BASE_HEADERS = {
        'Accept': '*/*',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'en-US,en;q=0.9,nl;q=0.8',
        'Cache-Control': 'no-cache',
        'DNT': '1',
        'TE': 'trailers',
        'Origin': 'https://www.ziggogo.tv',
        'Pragma': 'no-cache',
        'Referer': 'https://www.ziggogo.tv/',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-site',
        'X-Device-Code': 'web'
    }
    ALLOWED_LICENSE_HEADERS = [
        "Accept",
        "Accept-Encoding",
        "Accept-Language",
        "Cache-Control",
        "Connection",
        "Content-Length",
        "Cookie",
        "deviceName",
        "DNT",
        "Host",
        "Origin",
        "Pragma",
        "Referer",
        "Sec-Fetch-Dest",
        "Sec-Fetch-Mode",
        "Sec-Fetch-Site",
        "TE",
        "User-Agent",
        "X-cus",
        "x-drm-schemeId",
        "x-go-dev",
        "X-OESP-Username",
        "X-Profile",
        "x-streaming-token",
        "x-tracking-id"
    ]
    SERIES = 'Series'
    MOVIES = 'Movies'
    GENRES = 'Genre'
    def __init__(self):
        pass


G = GlobalVariables()

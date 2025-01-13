from Cryptodome.Cipher import AES
from pubnub.crypto import PubNubCryptoModule, AesCbcCryptoModule
from pubnub.pnconfiguration import PNConfiguration
from pubnub.pubnub import PubNub
from pubnub.models.consumer.v3.channel import Channel
from pubnub.models.consumer.v3.group import Group
from pubnub.models.consumer.v3.uuid import UUID
from .config import config

pubnub_config = config.get("PUBNUB")

cipher_key = pubnub_config.get("PUBNUB_CIPHER_KEY")

pn_config = PNConfiguration()
pn_config.publish_key = pubnub_config.get("PUBNUB_PUBLISH_KEY") 
pn_config.subscribe_key = pubnub_config.get("PUBNUB_SUBSCRIBE_KEY") 
pn_config.uuid = pubnub_config.get("PUBNUB_UUID") 
pn_config.secret_key = pubnub_config.get("PUBNUB_SECRET_KEY")
pn_config.cipher_key = cipher_key
pn_config.cipher_mode = AES.MODE_GCM
pn_config.fallback_cipher_mode = AES.MODE_CBC
pn_config.crypto_module = AesCbcCryptoModule(pn_config)
pubnub = PubNub(pn_config)

pi_channel = "Tempify"    #change?


def grant_read_access(user_id):
    print(f"GRANTING READ ACCESS {user_id}")
    envelope = pubnub.grant_token() \
    .channels([Channel.id("Tempify").read()]) \
    .authorized_uuid(user_id) \
    .ttl(60) \
    .sync()
    return envelope.result.token

def grant_write_access(user_id):
    print(f"GRANTING WRITE ACCESS {user_id}")
    envelope = pubnub.grant_token() \
    .channels([Channel.id("Tempify").write()]) \
    .authorized_uuid(user_id) \
    .ttl(60) \
    .sync()
    return envelope.result.token

def grant_read_write_access(user_id):
    print(f"GRANTING READ AND WRITE ACCESS {user_id}")
    envelope = pubnub.grant_token() \
    .channels([Channel.id("Tempify").read().write()]) \
    .authorized_uuid(user_id) \
    .ttl(60) \
    .sync()
    return envelope.result.token



def revoke_access(token):
    envelope = pubnub.revoke_token(token)


def parse_token(token):
    try:
        token_details = pubnub.parse_token(token)
        print("Parsing the token")
        print(token_details)

        # Safely access channel permissions
        channels = token_details.get("resources", {}).get("channels", {})
        channel_details = channels.get("Tempify", {})

        read_access = channel_details.get("read", False)
        write_access = channel_details.get("write", False)
        uuid = token_details.get("authorized_uuid")

        return token_details["timestamp"], token_details["ttl"], uuid, read_access, write_access
    except Exception as e:
        print(f"Error while parsing token: {e}")
        return None, None, None, False, False




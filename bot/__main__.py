from bot.discord import TorobooruClient
from bot.utils import (
    build_argument_parser,
    parse_environment_variables_to_namespace,
    get_settings_using_namespace
)
import ujson

argument_parser = build_argument_parser()

namespace = argument_parser.parse_args()
namespace = parse_environment_variables_to_namespace(namespace)

namespace.discord_text_channels = ujson.loads(namespace.discord_text_channels) \
    if namespace.discord_text_channels else []

database_connection_settings, storage_connection_settings = \
    get_settings_using_namespace(namespace)

client = TorobooruClient(database_connection_settings,
                         storage_connection_settings,
                         namespace.discord_text_channels)
client.run(namespace.discord_token, root_logger=True)

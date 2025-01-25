from typing import Optional, List, Any
from time import sleep
import requests

from settings import back_settings


class Readiness:
    """Class that handles /readiness endpoint."""

    urls: Optional[List[str]] = None
    logger: Any = None

    def __init__(
        self,
        urls: List[str],
        logger: Any,
    ) -> None:
        """
        :param urls: list of service urls to check.
        :param task: list of futures or coroutines
        :param logger: Logger object.
        :param client: HTTPClient object.
        """

        Readiness.urls = urls or []
        Readiness.logger = logger

        Readiness.status = False

    @classmethod
    def _make_request(cls, url: str) -> None:
        """Check readiness of the specified service."""

        while True:
            cls.logger.info(
                f"Trying to connect to '{url}'",
            )
            try:
                response = requests.get(url=f"{url}", timeout=back_settings.HC_TIMEOUT)
                if response.status_code:
                    cls.logger.info(
                        f"Successfully connected to '{url}'",
                    )
                    break

                cls.logger.warning(
                    f"Failed to connect to '{url}'",
                )
            except Exception as e:
                cls.logger.warning(
                    f"Failed to connect to '{url}': {str(e)}",
                )

            sleep(back_settings.HC_SLEEP)

    @classmethod
    def _check_readiness(cls) -> None:
        """Check readiness of all services."""

        cls.logger.info(
            f"Running readiness checks.",
        )
        [cls._make_request(url) for url in cls.urls or []]

        cls.logger.info(
            f"Successfully finished readiness checks.",
        )

    @classmethod
    def run(cls) -> None:
        cls._check_readiness()

from typing import Mapping, Optional, Set

from sentry.sentry_metrics.configuration import UseCaseKey
from sentry.sentry_metrics.indexer.base import KeyResult, KeyResults, StringIndexer
from sentry.sentry_metrics.indexer.id_generator import reverse_bits
from sentry.utils.codecs import Codec

EncodedId = int
DecodedId = int


class IdCodec(Codec[DecodedId, EncodedId]):
    """
    Reverses 64 bit IDs for storage and converts between uint64 (ClickHouse) and int64
    (CloudSpanner). IDs generated by our id_generator are incrementing and prefixed
    with a fixed version but we need well distributed primary keys to spread the work evenly
    between CloudSpanner nodes.
    """

    def encode(self, value: DecodedId) -> EncodedId:
        return reverse_bits(value, 64) - pow(2, 63)

    def decode(self, value: EncodedId) -> DecodedId:
        return reverse_bits(value + pow(2, 63), 64)


class CloudSpannerIndexer(StringIndexer):
    def bulk_record(
        self, use_case_id: UseCaseKey, org_strings: Mapping[int, Set[str]]
    ) -> KeyResults:
        # Currently just calls record() on each item. We may want to consider actually recording
        # in batches though.
        key_results = KeyResults()

        for (org_id, strings) in org_strings.items():
            for string in strings:
                result = self.record(use_case_id, org_id, string)
                key_results.add_key_result(KeyResult(org_id, string, result))

        return key_results

    def record(self, use_case_id: UseCaseKey, org_id: int, string: str) -> Optional[int]:
        raise NotImplementedError

    def resolve(self, use_case_id: UseCaseKey, org_id: int, string: str) -> Optional[int]:
        raise NotImplementedError

    def reverse_resolve(self, use_case_id: UseCaseKey, id: int) -> Optional[str]:
        raise NotImplementedError

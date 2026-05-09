# { "Depends": "py-genlayer:15qfivjvy80800rh998pcxmd2m8va1wq2qzqhz850n8ggcr4i9q0" }
from genlayer import *


def _norm_sentiment(s) -> str:
    s = str(s).strip().upper()
    for w in ("POSITIVE", "NEGATIVE", "NEUTRAL"):
        if w in s:
            return w
    return "NEUTRAL"


class SentimentBenchmark(gl.Contract):
    """
    Benchmark: Sentiment Analysis
    Tests equivalence principles on subjective NLP tasks
    with varying prompt complexity and model configurations.
    """
    texts: DynArray[str]

    def __init__(self):
        self.texts = [
            "The product was absolutely amazing, best purchase ever!",
            "Terrible experience, would not recommend to anyone.",
            "It was okay, nothing special but not bad either.",
            "Worst customer service I have ever encountered in my life.",
            "Decent quality for the price, satisfied overall.",
            "This is a masterpiece of modern engineering.",
            "Completely broken after one day of use. Fraud.",
            "Neutral opinion: pros and cons balance each other.",
            "Slightly disappointed but still usable.",
            "Exceeded all expectations, stellar performance.",
        ]

    @gl.public.write
    def benchmark_strict(self) -> str:
        """strict_eq on a single normalized sentiment label."""
        text = self.texts[0]

        def _analyze():
            result = gl.nondet.exec_prompt(
                f"Classify the sentiment of this text. "
                f"Respond as JSON with field 'sentiment' set to exactly one of: POSITIVE, NEGATIVE, NEUTRAL.\n"
                f"Text: {text}",
                response_format="json",
            )
            return _norm_sentiment(result.get("sentiment", ""))

        return gl.eq_principle.strict_eq(_analyze)

    @gl.public.write
    def benchmark_prompt_comparative(self) -> str:
        """prompt_comparative: LLM judge compares sentiment labels."""
        texts = list(self.texts[:3])

        def _analyze():
            result = gl.nondet.exec_prompt(
                f"Classify the sentiment of each text. "
                f"Respond as JSON with field 'labels' — an array of strings, each being POSITIVE, NEGATIVE, or NEUTRAL, in the same order as the input.\n"
                f"Texts: {texts}",
                response_format="json",
            )
            labels = result.get("labels", []) or []
            normalized = [_norm_sentiment(x) for x in labels]
            return " | ".join(normalized)

        return gl.eq_principle.prompt_comparative(
            _analyze,
            principle="The sentiment label (POSITIVE/NEGATIVE/NEUTRAL) for each text must match."
        )

    @gl.public.write
    def benchmark_custom(self) -> str:
        """custom: validator compares sentiment field directly using gl.vm.run_nondet."""
        text = self.texts[0]

        def _leader_fn():
            return gl.nondet.exec_prompt(
                f"Classify the sentiment of this text. "
                f"Respond as JSON with field 'sentiment' set to exactly one of: POSITIVE, NEGATIVE, NEUTRAL.\n"
                f"Text: {text}",
                response_format="json",
            )

        def _validator_fn(leaders_res) -> bool:
            if not isinstance(leaders_res, gl.vm.Return):
                return False
            try:
                my_result = _leader_fn()
                l = _norm_sentiment(leaders_res.calldata.get("sentiment", ""))
                v = _norm_sentiment(my_result.get("sentiment", ""))
                return l == v
            except Exception:
                return False

        result = gl.vm.run_nondet(_leader_fn, _validator_fn)
        return _norm_sentiment(result.get("sentiment", "") if isinstance(result, dict) else result)

    @gl.public.view
    def get_texts(self) -> DynArray[str]:
        return self.texts

# { "Depends": "py-genlayer:15qfivjvy80800rh998pcxmd2m8va1wq2qzqhz850n8ggcr4i9q0" }
from genlayer import *



class VisionPatternBenchmark(gl.Contract):
    """
    Benchmark: Vision / Multimodal Pattern Recognition
    Fetches standard test images and tests semantic alignment
    across multimodal validators.
    """
    image_urls: DynArray[str]

    def __init__(self):
        self.image_urls = [
            "https://upload.wikimedia.org/wikipedia/en/7/73/Trollface.png",
            "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4b/Up_arrow_icon.svg/1280px-Up_arrow_icon.svg.png",
            "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3a/Line_chart_icon.svg/1280px-Line_chart_icon.svg.png",
            "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e4/Screenshot_example.png/800px-Screenshot_example.png",
            "https://upload.wikimedia.org/wikipedia/commons/thumb/5/57/Capture_d%27%C3%A9cran_2023-08-14_120000.png/640px-Capture_d%27%C3%A9cran_2023-08-14_120000.png",
            "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a6/Pie_chart_icon.svg/1280px-Pie_chart_icon.svg.png",
            "https://upload.wikimedia.org/wikipedia/commons/thumb/8/87/PDF_file_icon.svg/1280px-PDF_file_icon.svg.png",
            "https://upload.wikimedia.org/wikipedia/commons/thumb/1/17/Warning_icon.svg/1280px-Warning_icon.svg.png",
            "https://upload.wikimedia.org/wikipedia/commons/thumb/9/91/Octicons-mark-github.svg/1280px-Octicons-mark-github.svg.png",
            "https://upload.wikimedia.org/wikipedia/commons/thumb/0/08/QR_code_example.png/1280px-QR_code_example.png",
        ]

    @gl.public.write
    def benchmark_prompt_comparative(self) -> str:
        """
        Multimodal consensus: describe each image semantically.
        Uses prompt_comparative for semantic alignment.
        """
        def _describe():
            descriptions = []
            for url in self.image_urls[:3]:
                desc = gl.nondet.exec_prompt(
                    f"Describe the image at this URL in one sentence. URL: {url}"
                )
                descriptions.append(desc.strip())
            return " | ".join(descriptions)
        return gl.eq_principle.prompt_comparative(
            _describe,
            principle="Each image description must refer to the same primary subject or category."
        )

    @gl.public.write
    def benchmark_custom(self) -> str:
        """
        custom: descriptions match if primary object label agrees for each image.
        Uses gl.advanced.run_nondet with custom comparator.
        """
        def _describe():
            labels = []
            for url in self.image_urls[:3]:
                desc = gl.nondet.exec_prompt(
                    f"Name the PRIMARY object in the image at this URL. Reply with ONE word only. URL: {url}"
                )
                labels.append(desc.strip().lower())
            return " | ".join(labels)

        def _validator(leaders):
            my_res, leaders_res = gl.advanced.validator_handle_rollbacks_and_errors_default(_describe, leaders)
            return str(my_res).strip().lower() == str(leaders_res).strip().lower()

        return gl.advanced.run_nondet(_describe, _validator)

    @gl.public.view
    def get_image_urls(self) -> DynArray[str]:
        return self.image_urls

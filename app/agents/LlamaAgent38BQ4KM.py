from subprocess import Popen, PIPE, run
from typing import Iterable

class _Llama38BQ4KM:
    # required by the loader
    name  = "LlamaAgent38BQ4KM"
    model = "llama3:8b-instruct-q4_K_M"

    def _invoke(self, prompt: str, stream: bool):
        cmd = ["ollama", "run", self.model]

        if stream:
            proc = Popen(cmd, stdin=PIPE, stdout=PIPE, text=True)
            proc.stdin.write(prompt)
            proc.stdin.close()
            for line in iter(proc.stdout.readline, ""):
                yield line
            proc.wait()
        else:
            out = run(cmd, input=prompt, text=True, capture_output=True, check=True)
            yield out.stdout

    # the loader calls this
    def run(self, text: str, stream: bool = False) -> Iterable[str] | str:
        return self._invoke(text, stream)

# what FastAPI looks for
agent = _Llama38BQ4KM()

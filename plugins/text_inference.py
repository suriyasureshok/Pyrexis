from core.base_pipeline import BasePipeline


class TextInferencePipeline(BasePipeline):
    name = "text_inference"

    def stages(self):
        return [
            self.preprocess,
            self.fake_model_call,
            self.postprocess,
        ]

    def preprocess(self, payload):
        return payload["prompt"].strip()

    def fake_model_call(self, text):
        return f"MODEL_OUTPUT({text})"

    def postprocess(self, output):
        return {"result": output}

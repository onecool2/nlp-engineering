from langchain.llms.base import LLM
from typing import Dict, List, Any, Optional
import torch,sys,os
from transformers import AutoTokenizer


class Llama2(LLM): # LLM是一个抽象类，需要实现_call方法
    max_token: int = 2048     # 最大token数
    temperature: float = 0.1  # 生成温度
    top_p: float = 0.95       # 生成概率
    tokenizer: Any            # 分词器
    model: Any                # 模型
    
    def __init__(self, model_name_or_path, bit4=True):
        super().__init__()
        self.tokenizer = AutoTokenizer.from_pretrained(model_name_or_path,use_fast=False)
        self.tokenizer.pad_token = self.tokenizer.eos_token
        if bit4==False: # 32bit
            from transformers import AutoModelForCausalLM
            self.model = AutoModelForCausalLM.from_pretrained(model_name_or_path,device_map='auto',torch_dtype=torch.float16,load_in_8bit=True)
            self.model.eval()
        else: # 4bit
            from auto_gptq import AutoGPTQForCausalLM
            self.model = AutoGPTQForCausalLM.from_quantized(model_name_or_path,low_cpu_mem_usage=True, device="cuda:0", use_triton=False,inject_fused_attention=False,inject_fused_mlp=False)
            
        if torch.__version__ >= "2" and sys.platform != "win32":
            self.model = torch.compile(self.model)
            
    @property # @property装饰器将方法转换为属性
    def _llm_type(self) -> str:
        return "Llama2"

    def _call(self, prompt: str, stop: Optional[List[str]] = None) -> str:
        print('prompt:',prompt)
        input_ids = self.tokenizer(prompt, return_tensors="pt",add_special_tokens=False).input_ids.to('cuda')
        generate_input = {
            "input_ids":input_ids,
            "max_new_tokens":1024,
            "do_sample":True,
            "top_k":50,
            "top_p":self.top_p,
            "temperature":self.temperature,
            "repetition_penalty":1.2,
            "eos_token_id":self.tokenizer.eos_token_id,
            "bos_token_id":self.tokenizer.bos_token_id,
            "pad_token_id":self.tokenizer.pad_token_id
        }
        generate_ids = self.model.generate(**generate_input)
        generate_ids = [item[len(input_ids[0]):-1] for  item in generate_ids]
        result_message = self.tokenizer.batch_decode(generate_ids, skip_special_tokens=True, clean_up_tokenization_spaces=False)[0]
        return result_message # 返回生成的文本

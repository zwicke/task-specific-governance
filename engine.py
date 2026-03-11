from typing import List, Dict
from pydantic import BaseModel

HARDWARE_REGISTRY = {
    "H100 SXM": {"bandwidth_gbs": 3350, "carbon_g_hr": 280}, 
    "A100 SXM": {"bandwidth_gbs": 2039, "carbon_g_hr": 350}, 
    "TPU v6e": {"bandwidth_gbs": 820, "carbon_g_hr": 45},
    "Shared": {"bandwidth_gbs": 150, "carbon_g_hr": 600}
}

class InferenceConfig(BaseModel):
    model_name: str
    provider: str
    hardware: str
    quality: int
    task_scores: Dict[str, int]  # e.g., {"Summarization": 9, "Coding": 4}
    billing_type: str 
    input_price: float 
    output_price: float
    parameters_billions: float 
    quantization_bits: int

    def calculate_normalized_cost(self) -> float:
        if self.billing_type == "token":
            return (self.input_price + self.output_price) / 2
        tokens_per_hour = 50 * 3600 
        return (self.output_price / tokens_per_hour) * 1_000_000

    def get_roofline_latency(self) -> float:
        hw = HARDWARE_REGISTRY.get(self.hardware, HARDWARE_REGISTRY["Shared"])
        model_size_gb = (self.parameters_billions * self.quantization_bits) / 8
        return (model_size_gb / hw["bandwidth_gbs"]) * 1000 * 1.2

    def get_carbon_footprint(self) -> float:
        hw = HARDWARE_REGISTRY.get(self.hardware, HARDWARE_REGISTRY["Shared"])
        hours_per_1m = (self.get_roofline_latency() * 1000000) / 3600000
        return hours_per_1m * hw["carbon_g_hr"]
    
    def get_weighted_task_performance(self, task_weights: Dict[str, float]) -> float:
        """Calculates performance based on the user's specific task mix."""
        score = 0.0
        for task, weight in task_weights.items():
            score += self.task_scores.get(task, 5) * weight
        return score

def get_pareto_frontier(configs: List[InferenceConfig]):
    frontier = []
    data_list = [
        {"c": c, "cost": c.calculate_normalized_cost(), "lat": c.get_roofline_latency(), "carbon": c.get_carbon_footprint()} 
        for c in configs
    ]
    for a in data_list:
        is_dominated = any(
            (b["cost"] <= a["cost"] and b["lat"] <= a["lat"] and b["c"].quality >= a["c"].quality and b["carbon"] <= a["carbon"]) and
            (b["cost"] < a["cost"] or b["lat"] < a["lat"] or b["c"].quality > a["c"].quality or b["carbon"] < a["carbon"])
            for b in data_list
        )
        if not is_dominated: frontier.append(a["c"])
    return frontier

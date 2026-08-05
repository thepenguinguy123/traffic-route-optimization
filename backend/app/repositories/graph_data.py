import math
import random
from typing import Dict, List, Any, Tuple

# 56 nodes của Quận 1, TP.HCM
NODES: Dict[str, Dict[str, Any]] = {
    "1": {"name": "Point 1", "lat": 10.7918511, "lng": 106.6958498},
    "2": {"name": "Point 2", "lat": 10.7902602, "lng": 106.694281},
    "3": {"name": "Point 3", "lat": 10.7878881, "lng": 106.6919386},
    "4": {"name": "Point 4", "lat": 10.7870447, "lng": 106.6911124},
    "5": {"name": "Point 5", "lat": 10.7859034, "lng": 106.689985},
    "6": {"name": "Point 6", "lat": 10.7849539, "lng": 106.6891118},
    "7": {"name": "Point 7", "lat": 10.7908431, "lng": 106.6970064},
    "8": {"name": "Point 8", "lat": 10.7903462, "lng": 106.6965149},
    "9": {"name": "Point 9", "lat": 10.7899509, "lng": 106.6961407},
    "10": {"name": "Point 10", "lat": 10.7892052, "lng": 106.6954145},
    "11": {"name": "Point 11", "lat": 10.7834747, "lng": 106.6907609},
    "12": {"name": "Point 12", "lat": 10.7903735, "lng": 106.6974895},
    "13": {"name": "Point 13", "lat": 10.7898822, "lng": 106.6970413},
    "14": {"name": "Point 14", "lat": 10.7894648, "lng": 106.6966329},
    "15": {"name": "Point 15", "lat": 10.7887819, "lng": 106.6959752},
    "16": {"name": "Point 16", "lat": 10.7883731, "lng": 106.6955677},
    "17": {"name": "Point 17", "lat": 10.7880648, "lng": 106.6952431},
    "18": {"name": "Point 18", "lat": 10.7875383, "lng": 106.6947312},
    "19": {"name": "Point 19", "lat": 10.7864692, "lng": 106.6937058},
    "20": {"name": "Point 20", "lat": 10.7860735, "lng": 106.693321},
    "21": {"name": "Point 21", "lat": 10.7855176, "lng": 106.6927936},
    "22": {"name": "Point 22", "lat": 10.7843547, "lng": 106.691675},
    "23": {"name": "Point 23", "lat": 10.7894405, "lng": 106.6985103},
    "24": {"name": "Point 24", "lat": 10.7889364, "lng": 106.6980613},
    "25": {"name": "Point 25", "lat": 10.7885592, "lng": 106.6977187},
    "26": {"name": "Point 26", "lat": 10.7899243, "lng": 106.6979905},
    "27": {"name": "Point 27", "lat": 10.7894026, "lng": 106.6975383},
    "28": {"name": "Point 28", "lat": 10.7890503, "lng": 106.6971662},
    "29": {"name": "Point 29", "lat": 10.7874246, "lng": 106.6966256},
    "30": {"name": "Point 30", "lat": 10.7865695, "lng": 106.6957979},
    "31": {"name": "Point 31", "lat": 10.785581, "lng": 106.6948634},
    "32": {"name": "Point 32", "lat": 10.7814733, "lng": 106.6929031},
    "33": {"name": "Point 33", "lat": 10.7884831, "lng": 106.6995536},
    "34": {"name": "Point 34", "lat": 10.7880034, "lng": 106.6990605},
    "35": {"name": "Point 35", "lat": 10.7864747, "lng": 106.6976387},
    "36": {"name": "Point 36", "lat": 10.7856022, "lng": 106.6968275},
    "37": {"name": "Point 37", "lat": 10.7847069, "lng": 106.695946},
    "38": {"name": "Point 38", "lat": 10.7835837, "lng": 106.6948873},
    "39": {"name": "Point 39", "lat": 10.7824177, "lng": 106.6937661},
    "40": {"name": "Point 40", "lat": 10.7855356, "lng": 106.698648},
    "41": {"name": "Point 41", "lat": 10.786592, "lng": 106.7015616},
    "42": {"name": "Point 42", "lat": 10.7845956, "lng": 106.6996555},
    "43": {"name": "Point 43", "lat": 10.7837385, "lng": 106.698821},
    "44": {"name": "Point 44", "lat": 10.7838141, "lng": 106.6970298},
    "45": {"name": "Point 45", "lat": 10.7846594, "lng": 106.6978411},
    "46": {"name": "Point 46", "lat": 10.7829021, "lng": 106.6980713},
    "47": {"name": "Point 47", "lat": 10.7817021, "lng": 106.6969469},
    "48": {"name": "Point 48", "lat": 10.7805513, "lng": 106.6958432},
    "49": {"name": "Point 49", "lat": 10.7795911, "lng": 106.6949881},
    "50": {"name": "Point 50", "lat": 10.780493, "lng": 106.6939512},
    "51": {"name": "Point 51", "lat": 10.781489, "lng": 106.6948229},
    "52": {"name": "Point 52", "lat": 10.7829581, "lng": 106.695588},
    "53": {"name": "Point 53", "lat": 10.7829291, "lng": 106.6961808},
    "54": {"name": "Point 54", "lat": 10.7823626, "lng": 106.6961969},
    "55": {"name": "Point 55", "lat": 10.782138, "lng": 106.6964902},
    "56": {"name": "Point 56", "lat": 10.7823409, "lng": 106.6955863}
}


def haversine_distance(node1: str, node2: str) -> float:
    """
    Tính khoảng cách Haversine giữa 2 nodes (km).
    
    Args:
        node1: ID của node thứ nhất
        node2: ID của node thứ hai
        
    Returns:
        float: Khoảng cách giữa 2 nodes (km), trả về inf nếu node không tồn tại
    """
    if node1 not in NODES or node2 not in NODES:
        return float('inf')
        
    lat1, lon1 = NODES[node1]["lat"], NODES[node1]["lng"]
    lat2, lon2 = NODES[node2]["lat"], NODES[node2]["lng"]
    R = 6371.0  # Bán kính Trái Đất (km)

    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * 
         math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def _build_edges() -> List[Dict[str, Any]]:
    """
    Xây dựng danh sách edges từ nodes.
    Mỗi node kết nối với 3-5 node gần nhất.
    
    Returns:
        List[Dict]: Danh sách edges với thông tin distance, time, congestion
    """
    edges: List[Dict[str, Any]] = []
    random.seed(42)  # Fixed seed cho reproducibility
    node_ids = list(NODES.keys())
    edge_set = set()

    for i in range(len(node_ids)):
        distances = []
        for j in range(len(node_ids)):
            if i != j:
                dist = haversine_distance(node_ids[i], node_ids[j])
                distances.append((dist, node_ids[j]))
        
        distances.sort()
        num_connections = random.randint(3, 5)
        for dist, target in distances[:num_connections]:
            u, v = node_ids[i], target
            if u > v:
                u, v = v, u
            
            if (u, v) not in edge_set:
                edge_set.add((u, v))
                time_min = max(1, int((dist / 25.0) * 60) + random.randint(1, 3))
                congestion = random.randint(1, 10)
                
                edges.append({
                    "from": u,
                    "to": v,
                    "distance_km": round(dist, 3),
                    "time_min": time_min,
                    "congestion": congestion
                })
                edges.append({
                    "from": v,
                    "to": u,
                    "distance_km": round(dist, 3),
                    "time_min": time_min,
                    "congestion": congestion
                })
    return edges


EDGES: List[Dict[str, Any]] = _build_edges()


def calculate_cost(edge: Dict[str, Any], cost_type: str = "distance") -> float:
    """
    Tính chi phí của một edge dựa trên loại chi phí.
    
    Args:
        edge: Dictionary chứa thông tin edge (distance_km, time_min, congestion)
        cost_type: Loại chi phí ('distance', 'time', 'combined')
        
    Returns:
        float: Chi phí của edge
    """
    if cost_type == "distance":
        return edge["distance_km"]
    elif cost_type == "time":
        return edge["time_min"]
    elif cost_type == "combined":
        # Chi phí kết hợp: khoảng cách + thời gian + kẹt xe
        return edge["distance_km"] + (edge["time_min"] / 10.0) + (edge["congestion"] * 0.4)
    return edge["distance_km"]

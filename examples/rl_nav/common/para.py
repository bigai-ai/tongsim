import numpy as np

GRPC_ENDPOINT = "127.0.0.1:5726"
SUB_LEVEL = "/Game/Maps/Sublevels/SubLevel_005.SubLevel_005"

BP_AGENT = "/Game/TongSim/Characters/Weiguo_V01/BP_Weiguo.BP_Weiguo_C"
BP_PAPER_USED = "/Game/_Game/BP_Paper_Used.BP_Paper_Used_C"
GRID_SIZE = 128
VIEW_SIZE = 19
GRID_RES = 1400.0 / GRID_SIZE  # resolution of grid map. unit:cm
AGENT_COL_R = 5.0  # agent collision radius. unit:cm
AGENT_PIX = 1  # math.ceil(AGENT_COL_R / GRID_RES)   agent pix size
STEP_LEN = 2  # agent's move step length unit：pix
GOAL_COL_R = 16.0  # goal collision radius. unit:cm
GOAL_PIX = 1  # int(GOAL_COL_R / GRID_RES)  goal pix size
MAX_UPDATE_GOAL_STEPS = 50  # max steps for update high-level policy

# grid value
UNKNOW = 200
OBS = 255
FREE = 0
GOAL = 160
AGENT = 100

"""
coordinate transform
Continuous coordinate conversion to discrete coordinate

center  500   700    5
x_length=1400     -200->500   	500 ->1200
y_length=1400	  0->700      	700->1400
z_length=10       0->5   		5->10
x坐标平移到0->1400,需要+200
"""
ROOM_CENTER = (500, 700, 50)
TRANS_X = 200.0
ROOM_RES = (
    GRID_SIZE,
    GRID_SIZE,
    64,
)
ROOM_EXT = (700, 700, 45)

# List of feasible regions
AREA_LIST = [
    np.array([[510, 50], [650, 310]]),
    np.array([[500, 490], [620, 610]]),
    np.array([[520, 750], [620, 1050]]),
    np.array([[130, 540], [400, 620]]),
    np.array([[230, 980], [380, 1080]]),
    np.array([[180, 330], [450, 430]]),
    np.array([[650, 720], [750, 800]]),
]

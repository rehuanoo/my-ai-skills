import random
import time

# 设置屏幕大小
WIDTH, HEIGHT = 20, 20

# 蛇头的坐标
snake = [(10, 10)]  # (x, y)
direction = "right"  # 可以是 up, down, left, right

# 蛇的长度
length = 1

# 蛇的食物位置
food = (10, 10)

# 食物的移动速度
food_speed = 1

# 游戏循环
while True:
    # 更新蛇的位置
    new_head = (snake[0][0] + 1, snake[0][1] + 1)
    snake.insert(0, new_head)
    food = (random.randint(0, WIDTH-1), random.randint(0, HEIGHT-1))

    # 判断是否碰撞
    if new_head in snake:
        print("Game Over")
        break

    # 更新屏幕
    print("Snake: ", snake)
    print("Food: ", food)
    print("Direction: ", direction)
    print("Speed:", food_speed)

    # 重置食物位置
    food = (random.randint(0, WIDTH-1), random.randint(0, HEIGHT-1))

    time.sleep(0.1)

    # 重新设置方向
    direction = "right" if direction == "up" else "down" if direction == "left" else "right"

    # 检查是否在边界外
    if new_head[0] < 0 or new_head[0] >= WIDTH or new_head[1] < 0 or new_head[1] >= HEIGHT:
        print("Game Over")
        break

    # 删除蛇头
    snake.pop()

    # 重新设置方向
    direction = "right" if direction == "up" else "down" if direction == "left" else "right"

    # 重置食物
    food = (random.randint(0, WIDTH-1), random.randint(0, HEIGHT-1))

    # 重置蛇头
    snake = [(new_head[0], new_head[1])]
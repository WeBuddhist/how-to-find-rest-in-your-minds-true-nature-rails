

arr = [2,3,4,5,6,6]
max_ = max(arr)
sm = 0
for i in arr:
    if (sm<i and i<max_):
        sm =i
print(sm)

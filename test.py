import cv2

codecs = ['mp4v', 'XVID', 'MJPG', 'H264']
out_size = (320, 240)
fps = 10.0

for codec in codecs:
    fourcc = cv2.VideoWriter_fourcc(*codec)
    writer = cv2.VideoWriter(f'test_{codec}.avi', fourcc, fps, out_size)
    ok = writer.isOpened()
    writer.release()
    print(f'Codec {codec}: {"支持" if ok else "不支持"}')

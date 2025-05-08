"""
@Project ：Backend
@File    ：main.py
@Author  ：PySuper
@Date    ：2025/4/23 19:41
@Desc    ：Backend main.py
"""
import cv2
import numpy as np
import os


class MathC:
    def __init__(self):
        # 初始化人脸检测器
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        # 初始化人脸识别器
        self.recognizer = cv2.face.LBPHFaceRecognizer_create()
        self.trained = False
        self.labels = {}
        self.label_ids = {}
        self.next_id = 0

    def parse(self, params):
        """
        解析参数并执行相应的人脸识别操作

        参数格式：
        {
            "operation": "detect"|"train"|"recognize",
            "image_path": "图片路径",
            "name": "人名" (仅训练时需要)
        }

        返回：
        根据操作不同返回不同结果
        """
        operation = params.get("operation", "detect")

        if operation == "detect":
            return self.detect_faces(params.get("image_path"))
        elif operation == "train":
            return self.train_face(params.get("image_path"), params.get("name"))
        elif operation == "recognize":
            return self.recognize_face(params.get("image_path"))
        else:
            return {"error": "不支持的操作类型"}

    def detect_faces(self, image_path):
        """检测图片中的人脸位置"""
        if not os.path.exists(image_path):
            return {"error": "图片文件不存在"}

        image = cv2.imread(image_path)
        if image is None:
            return {"error": "无法读取图片"}

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30)
        )

        result = {
            "faces_count": len(faces),
            "faces": [{"x": int(x), "y": int(y), "width": int(w), "height": int(h)}
                     for (x, y, w, h) in faces]
        }

        return result

    def train_face(self, image_path, name):
        """训练人脸识别模型"""
        if not name:
            return {"error": "需要提供名称"}

        if not os.path.exists(image_path):
            return {"error": "图片文件不存在"}

        # 检测人脸
        detect_result = self.detect_faces(image_path)
        if detect_result.get("error"):
            return detect_result

        if detect_result["faces_count"] == 0:
            return {"error": "未检测到人脸"}

        if detect_result["faces_count"] > 1:
            return {"error": "图片中包含多个人脸，请提供只有一个人脸的图片"}

        # 读取图片并获取人脸区域
        image = cv2.imread(image_path)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        face = detect_result["faces"][0]
        x, y, w, h = face["x"], face["y"], face["width"], face["height"]
        roi_gray = gray[y:y+h, x:x+w]

        # 为新人脸分配ID
        if name not in self.label_ids:
            self.label_ids[name] = self.next_id
            self.labels[self.next_id] = name
            self.next_id += 1

        label_id = self.label_ids[name]

        # 准备训练数据
        faces = [roi_gray]
        labels = [label_id]

        # 训练模型
        if not self.trained:
            self.recognizer.train(faces, np.array(labels))
            self.trained = True
        else:
            self.recognizer.update(faces, np.array(labels))

        return {
            "status": "成功",
            "message": f"已成功添加 '{name}' 的人脸数据"
        }

    def recognize_face(self, image_path):
        """识别图片中的人脸"""
        if not self.trained:
            return {"error": "模型尚未训练，请先添加人脸数据"}

        # 检测人脸
        detect_result = self.detect_faces(image_path)
        if detect_result.get("error"):
            return detect_result

        if detect_result["faces_count"] == 0:
            return {"error": "未检测到人脸"}

        # 读取图片
        image = cv2.imread(image_path)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        results = []
        for face in detect_result["faces"]:
            x, y, w, h = face["x"], face["y"], face["width"], face["height"]
            roi_gray = gray[y:y+h, x:x+w]

            # 预测
            label_id, confidence = self.recognizer.predict(roi_gray)

            # 转换置信度为百分比 (LBPH返回的置信度越低越好)
            confidence_percentage = 100 - min(confidence, 100)

            name = self.labels.get(label_id, "未知")

            results.append({
                "name": name,
                "confidence": confidence_percentage,
                "position": {"x": x, "y": y, "width": w, "height": h}
            })

        return {
            "faces_count": len(results),
            "recognized_faces": results
        }

"""
# 初始化
math_c = MathC()

# 检测人脸
result = math_c.parse({
    "operation": "detect",
    "image_path": "/path/to/image.jpg"
})

# 训练人脸
result = math_c.parse({
    "operation": "train",
    "image_path": "/path/to/face_image.jpg",
    "name": "张三"
})

# 识别人脸
result = math_c.parse({
    "operation": "recognize",
    "image_path": "/path/to/unknown_face.jpg"
})
"""

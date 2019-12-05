import json
import cv2
import threading

class MqttMotionPublisher(threading.Thread):
    def __init__(self, client, topic_prefix, motion_changed, motion_flags):
        threading.Thread.__init__(self)
        self.client = client
        self.topic_prefix = topic_prefix
        self.motion_changed = motion_changed
        self.motion_flags = motion_flags

    def run(self):
        last_sent_motion = ""
        while True:
            with self.motion_changed:
                self.motion_changed.wait()
            
            # send message for motion
            motion_status = 'OFF'
            if any(obj.is_set() for obj in self.motion_flags):
                motion_status = 'ON'

            if last_sent_motion != motion_status:
                last_sent_motion = motion_status
                self.client.publish(self.topic_prefix+'/motion', motion_status, retain=False)

class MqttObjectPublisher(threading.Thread):
    def __init__(self, client, topic_prefix, objects_parsed, detected_objects):
        threading.Thread.__init__(self)
        self.client = client
        self.topic_prefix = topic_prefix
        self.objects_parsed = objects_parsed
        self._detected_objects = detected_objects

    def run(self):
        last_sent_payload = ""
        while True:

            # initialize the payload
            payload_bool = {}
            payload_numeric = {}

            # wait until objects have been parsed
            with self.objects_parsed:
                self.objects_parsed.wait()

            # add all the person, car, truck... scores in detected objects
            # average over past 1 seconds (5fps)
            detected_objects = self._detected_objects.copy()
            
            #NEW: now able to detect multiple objects - Brad
            to_detect = ["person", "bicycle", "car", "truck", "motorcycle", "bus", "dog"]
            for obj1 in detected_objects:
                if obj1['name'] in to_detect:
                    avg_object_score = (sum([obj['score'] for obj in detected_objects if obj['name'] == obj1['name']])/5)*100
                    
                    #for numeric mqtt topic
                    payload_numeric[obj1['name']] = int(avg_object_score)
                    
                    #for bool mqtt topic, also used to slow down mqtt traffic
                    payload_bool[obj1['name']] = 'FOUND' if int(avg_object_score) > 75 else 'NOT_FOUND'

            # send message for objects if different
            new_payload_bool = json.dumps(payload_bool, sort_keys=True)
            new_payload_numeric = json.dumps(payload_numeric, sort_keys=True)
            
            if new_payload_bool != last_sent_payload:
                last_sent_payload = new_payload_bool
                self.client.publish(self.topic_prefix+'/objects/numeric', new_payload_numeric, retain=False)
                self.client.publish(self.topic_prefix+'/objects/bool', new_payload_bool, retain=False)
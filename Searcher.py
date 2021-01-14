from elasticsearch import Elasticsearch
import sqlite3
import numpy as np
from facenet_pytorch import MTCNN, InceptionResnetV1
from PIL import Image


class Searcher:
    def __init__(self, address):
        self.es = Elasticsearch(address)

        self.face_model = InceptionResnetV1(pretrained='vggface2').eval()
        self.mtcnn = MTCNN()
        self.face_embeddings = np.load('models/face_embeddings.npy')
        self.embedding2img = np.load('models/embedding2img.npy')
        self.normalize = lambda x : x / np.linalg.norm(x)
        
        self.image_db = sqlite3.connect('data/images.db', check_same_thread = False)
        self.db_cursor = self.image_db.cursor()
    

    def search(self, keyword, domain, sorting='_score'):
        '''
        General interface for searching.

        Input: `keyword`: search command
               `domain`: search domain ('web', 'images', 'visual')
               `sorting`: method of sorting
        Output: `results`: info of the results
        '''
        results = []
        if domain == 'web':
            docs = self.bool_search('webpages', keyword, sorting={ sorting: 'desc' })
            for doc in docs:
                source = doc['_source']
                highlight = doc['highlight']
                results.append({
                    'title': highlight['title'][0] if 'title' in highlight else source['title'],
                    'link': '/article?id={}'.format(source['id']),
                    'url': source['url'],
                    'abstract': '...'.join(highlight['article']) if 'article' in highlight else ''
                })
        elif domain == 'images':
            docs = self.bool_search('images', keyword, fields=['description'], sorting={ sorting: 'desc' })
            for doc in docs:
                source = doc['_source']
                results.append({
                    'title': source['title'],
                    'url': source['url'],
                    'description': source['description'],
                    'action_url': '/article?id={}'.format(source['id'])
                })
        elif domain == 'visual':
            docs = self.face_search('upload/' + keyword)
            for doc in docs[:50]:
                imgs = eval(doc['images'])
                for image, description in imgs:
                    results.append({
                        'title': doc['title'],
                        'url': image,
                        'description': description,
                        'action_url': '/article?id={}'.format(doc['_id'])
                    })
        return results


    def parse_command(self, command):
        '''
        Parse the input command and convert it into a command dict.

        Input: `command`: query in the format `C site:S`
        Output: dict in the format `{ 'general': C, 'site': S }`
        '''
        allowed_opt = ['site']
        opt = 'general'
        command_dict = { opt: '' }

        for i in command.split(' '):
            if ':' in i:
                opt, value = i.split(':')
                opt = opt.lower()
                if opt in allowed_opt:
                    command_dict[opt] = value
            else:
                command_dict[opt] += ' ' + i
        return command_dict


    def bool_search(self, index, keyword, fields=['title', 'article'], sorting={'_score': 'desc'}):
        '''
        Bool search for elastic search.

        Input: `index`: index for search
               `keyword`: search command
               `fields`: fields for general searches
               `sorting`: method of sorting (default: score decending)
        Output: `result` from elastic search
        '''
        query = {
            "size": 50,
            "query": {
                "bool": {
                    "must": []
                }
            },
            "highlight": {
                "fields": {
                    "*": {
                        "pre_tags": ["<em>"],
                        "post_tags": ["</em>"]
                    }
                }
            },
            "sort": []
        }

        query_dict = self.parse_command(keyword)
        for key, value in query_dict.items():
            if key == 'general':
                query['query']['bool']['must'].append({
                    "multi_match": {
                        "query": value,
                        "fields": fields
                    }
                })
            else:
                query['query']['bool']['must'].append({
                    'match': { 
                        key: value 
                    }
                })
        
        for key, value in sorting.items():
            query['sort'].append({
                key: {
                    'order': value
                }
            })

        result = self.es.search(index=index, body=query)
        return result['hits']['hits']


    def face_search(self, image_path):
        try:
            img = Image.open(image_path)
            img_cropped = self.mtcnn(img)
            img_embedding = self.face_model(img_cropped.unsqueeze(0)).detach().numpy().reshape((512))
        except:
            raise RuntimeError("No face")

        distances = np.zeros(self.face_embeddings.shape[0])

        for i in range(self.face_embeddings.shape[0]):
            distances[i] = np.linalg.norm(img_embedding - self.face_embeddings[i])
        x = distances.argsort()[:100]

        least = 0
        while least < 100 and distances[x[least]] < 1.06:
            least += 1
        if least == 0:
            raise RuntimeError("Not found")

        result = []
        for i in range(least):
            index = int(self.embedding2img[x[i]])
            if index != -1:
                image_name = str(index) + '.jpg'
                res = list(self.db_cursor.execute("SELECT * FROM MSN WHERE fname='{}'".format(image_name)))[0]
                result.append({
                    'title': res[1],
                    'date': res[2],
                    'author': res[3],
                    'article': res[4],
                    'images': res[5],
                    'url': res[6],
                    'type': res[-1],
                    '_id': res[-5]
                })
        return result


    def __del__(self):
        self.es.close()
        self.db_cursor.close()

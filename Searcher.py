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
        self.embeddings = np.load('models/embeddings.npy')
        self.embeddings_img = np.load('models/embeddings_image.npy')
        self.normalize = lambda x : x / np.linalg.norm(x)
        
        self.image_db = sqlite3.connect('data/MSN_technology.db', check_same_thread = False)
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
                    'link': '/article?id={}'.format(source['article_id']),
                    'url': source['url'],
                    'abstract': source['description']
                })
        elif domain == 'visual':
            docs = self.face_search('upload/' + keyword)
            for doc in docs:
                source = doc
                results.append({
                    'title': source['title'],
                    'link': '/article?id={}'.format(source['article_id']),
                    'url': source['url'],
                    'abstract': source['description']
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
        '''
        Face search for specific image path.

        Input: `image_path`: path of the image uploaded
        Output: `result` of similar images
        '''
        try:
            image = Image.open(image_path)
            image_cropped = self.mtcnn(image)
            image_embedding = self.face_model(image_cropped.unsqueeze(0)).detach().numpy().reshape((512))
        except:
            raise RuntimeError("No face")

        distances = np.zeros(self.embeddings.shape[0])

        for i in range(self.embeddings.shape[0]):
            distances[i] = np.linalg.norm(image_embedding - self.embeddings[i])
        x = distances.argsort()[:100]

        least = 0
        while least < 100 and distances[x[least]] < 1.06:
            least += 1
        if least == 0:
            raise RuntimeError("Not found")

        result = []
        for i in range(min(least, 50)):
            _id = int(self.embeddings_img[x[i]])
            if _id != -1:
                res = list(self.db_cursor.execute("SELECT * FROM IMAGES WHERE _id = {}".format(_id)))[0]
                result.append({
                    '_id': res[0],
                    'url': res[1],
                    'description': res[2],
                    'article_id': res[3],
                    'title': res[4],
                    'author': res[5],
                    'date': res[6]
                })
        return result


    def __del__(self):
        self.es.close()
        self.db_cursor.close()

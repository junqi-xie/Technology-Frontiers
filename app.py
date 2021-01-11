import os, random

from flask import Flask, redirect, render_template, request, url_for, send_from_directory
import sqlite3

from Searcher import Searcher


app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'upload')


def get_article(id):
    '''
    Get specified article from the database.

    Input: `id`: id of the article
    Output: article infomation
    '''
    sql_text = "SELECT * FROM MSN WHERE _id='{}'".format(id)
    result = list(db_cursor.execute(sql_text))[0]
    info = {
        'id': result[0],
        'url': result[1],
        'title': result[2],
        'author': result[3],
        'date': result[4],
        'article': result[5],
        'images': eval(result[6]),
        'related': eval(result[7]),
    }
    return info


def render_main(request, template, domain):
    '''
    Render 'main' page for website and image search.

    Input: `request`: `request` variable received
           `template`: template HTML file
           `domain`: search domain
    '''
    if request.method == "POST":
        keyword = request.form['keyword']
        return redirect(url_for(domain + '_search', keyword=keyword))
    return render_template(template)


def render_results(request, template, domain):
    '''
    Render 'results' page for website and image search.

    Input: `request`: `request` variable received
           `template`: template HTML file
           `domain`: search domain
    '''
    if request.method == "POST":
        try:
            keyword = request.form['keyword']
            return redirect(url_for(domain + '_search', keyword=keyword))
        except:
            pass
        try:
            file = request.files['file']
            filename = file.filename
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            return redirect(url_for('visual_search', keyword=filename))
        except:
            pass
    
    keyword = request.args.get('keyword')
    sorting = '_score'
    if request.args.get('sorting'):
        sorting = request.args.get('sorting')
    results = searcher.search(keyword, domain, sorting)
    return render_template(template, keyword=keyword, results=results)


@app.route('/', methods=['POST', 'GET'])
def index():
    if request.method == "POST":
        keyword = request.form['keyword']
        return redirect(url_for('web_search', keyword=keyword))

    main = random.sample(range(15931), 3)
    content = list(map(lambda x: get_article(x), main))
    return render_template('index.html', content=content)


@app.route('/article', methods=['POST', 'GET'])
def article():
    if request.method == "POST":
        keyword = request.form['keyword']
        return redirect(url_for('web_search', keyword=keyword))

    id = request.args.get('id')
    content = get_article(id)
    content['article'] = '<p>' + '</p><p>'.join(content['article'].split('\n'))
    content['related'] = list(map(lambda x: get_article(x), content['related']))
    return render_template("article.html", content=content)


@app.route('/web', methods=['POST', 'GET'])
def web():
    return render_main(request, 'web.html', 'web')


@app.route('/web/search', methods=['POST', 'GET'])
def web_search():
    return render_results(request, 'web_results.html', 'web')


@app.route('/images', methods=['POST', 'GET'])
def images():
    return render_main(request, 'images.html', 'images')


@app.route('/images/search', methods=['POST', 'GET'])
def images_search():
    return render_results(request, 'images_results.html', 'images')


@app.route('/visual', methods=['POST', 'GET'])
def visual():
    if request.method == "POST":
        try:
            keyword = request.form['keyword']
            return redirect(url_for('images_search', keyword=keyword))
        except:
            pass
        try: 
            file = request.files['file']
            filename = file.filename
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            return redirect(url_for('visual_search', keyword=filename))
        except:
            pass
    return render_template('visual.html')


@app.route('/visual/search', methods=['POST', 'GET'])
def visual_search():
    return render_results(request, 'visual_results.html', 'visual')


searcher = None  # To be initialized in __main__
db_cursor = None  # To be initialized in __main__
if __name__ == '__main__':
    searcher = Searcher('http://localhost:9200/')
    db = sqlite3.connect('data/MSN.db', check_same_thread = False)
    db_cursor = db.cursor()
    app.run(debug=True, port=8080)

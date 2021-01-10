from flask import Flask, redirect, render_template, request, url_for
import sqlite3
from Searcher import Searcher


app = Flask(__name__)


def render_main(request, template, domain):
    '''
    Render 'main' page for website and image search.

    Input: `request`: `request` variable received
           `template`: template HTML file
           `domain`: search domain
    '''
    if request.method == "POST":
        keyword = request.form['keyword']
        return redirect(url_for(domain + '/search', keyword=keyword))
    return render_template(template)


def render_results(request, template, domain):
    '''
    Render 'results' page for website and image search.

    Input: `request`: `request` variable received
           `template`: template HTML file
           `domain`: search domain
    '''
    if request.method == "POST":
        if request.form['keyword']:
            keyword = request.form['keyword']
            return redirect(url_for(domain + '/search', keyword=keyword))
        else:
            f = request.files['file']
            f.save('upload/' + f.filename)
            return redirect(url_for(domain + '/search', keyword=f.filename))
    
    keyword = request.args.get('keyword')
    results = searcher.search(keyword, domain)
    return render_template(template, keyword=keyword, results=results)


@app.route('/', methods=['POST', 'GET'])
def index():
    if request.method == "POST":
        keyword = request.form['keyword']
        return redirect(url_for('web/search', keyword=keyword))
    return render_template('index.html')


@app.route('/article', methods=['POST', 'GET'])
def article():
    if request.method == "POST":
        keyword = request.form['keyword']
        return redirect(url_for('web/search', keyword=keyword))

    _id = request.args.get('id')
    sql_text = "SELECT * FROM MSN WHERE _id='{}'".format(_id)
    result = list(db_cursor.execute(sql_text))[0]
    content = {
        'title': result[0],
        'date': result[1],
        'author': result[2],
        'article': result[6]
    }
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
        if request.form['keyword']:
            keyword = request.form['keyword']
            return redirect(url_for('images/search', keyword=keyword))
        else:
            f = request.files['file']
            f.save('upload/' + f.filename)
            return redirect(url_for('visual/search', keyword=f.filename))
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

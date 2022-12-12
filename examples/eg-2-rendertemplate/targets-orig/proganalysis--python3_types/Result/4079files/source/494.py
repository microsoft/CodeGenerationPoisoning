import copy
import re
from flask import render_template, url_for, request, redirect
from www import app, cache
from www.codepoint import hex2id


@app.before_first_request
def init():
    app.uinfo.load()


@app.route("/")
def welcome():
    blocks = app.uinfo.get_block_infos()
    half = int(len(blocks) / 2)
    data = {
        "chars": app.uinfo.get_random_char_infos(32),
        "blocks1": blocks[:half],
        "blocks2": blocks[half:],
    }
    return render_template("welcome.html", data=data)


@app.route("/sitemap.txt")
@cache.memoize(120)
def sitemap():
    return render_template("sitemap.txt", blocks=app.uinfo.get_block_infos())


@app.route("/robots.txt")
@cache.memoize(120)
def robots():
    return render_template("robots.txt")


@app.route("/c/<char_code>")
@cache.memoize(120)
def show_code(char_code):
    if not re.match(r"^[0-9A-Fa-f]{1,6}$", char_code):
        return render_template("404.html")
    char_id = hex2id(char_code.lower())
    codepoint = app.uinfo.get_char(char_id)
    if codepoint is None:
        return render_template("404.html")
    info = {}
    info["codepoint"] = codepoint

    info["related"] = [
        app.uinfo.get_char_info(code_related) for code_related in codepoint.related
    ]
    info["confusables"] = [
        app.uinfo.get_char_info(code_confusable)
        for code_confusable in codepoint.confusables
    ]

    combinables = []
    for combinable in codepoint.combinables:
        combinables.append(
            [app.uinfo.get_char_info(codepoint_id) for codepoint_id in combinable]
        )
    info["combinables"] = combinables

    info["case"] = app.uinfo.get_char_info(codepoint.case)
    info["prev"] = app.uinfo.get_char_info(codepoint.prev)
    info["next"] = app.uinfo.get_char_info(codepoint.next)
    info["block"] = app.uinfo.get_block_info(codepoint.block)
    info["subblock"] = app.uinfo.get_subblock(codepoint.subblock)

    return render_template("code.html", data=info)


@app.route("/code/<code>")
def show_code_old(code):
    return redirect(url_for("show_code", char_code=code))


@app.route("/b/<block_code>")
@cache.memoize(120)
def show_block(block_code):
    if not re.match(r"^[0-9A-Fa-f]{1,6}$", block_code):
        return render_template("404.html")

    block_id = hex2id(block_code.lower())
    block = app.uinfo.get_block(block_id)
    if not block:
        return render_template("404.html")

    info = {}
    info["block"] = block

    chars = []
    for codepoint in block.codepoints_iter():
        chars.append(app.uinfo.get_char_info(codepoint))
    info["chars"] = chars

    info["prev"] = app.uinfo.get_block_info(block.prev)
    info["next"] = app.uinfo.get_block_info(block.next)

    return render_template("block.html", data=info)


@app.route("/block/<name>")
def show_block_old(name):
    block_id = app.uinfo.get_block_id_by_name(name)
    if block_id is not None:
        return redirect(url_for("show_block", code="{:04X}".format(block_id)))
    return render_template("404.html")


@app.route("/search", methods=["POST"])
def search():
    query = request.form["q"]
    app.logger.info("get /search/{}".format(query))
    matches, msg = app.uinfo.search_by_name(query, 100)
    return render_template("search_results.html", query=query, msg=msg, matches=matches)


@app.route("/search", methods=["GET"])
def search_bad_method():
    return redirect("/")

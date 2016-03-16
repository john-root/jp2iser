import jp2iser
from flask import Flask, request, jsonify

app = Flask(__name__)
app.config.from_object(__name__)


@app.route("/convert", methods=["POST"])
def convert():

    data = request.get_json()
    job_id = data.get("jobId")
    source = data.get("source")
    destination = data.get("destination")
    thumb_dir = data.get("thumbDir")
    optimisation = data.get("optimisation")
    if thumb_dir and thumb_dir[-1] != "/":
        thumb_dir += "/"
    thumb_sizes = data.get("thumbSizes")

    # TODO check rest for Noneness
    if source is not None:
        # currently no idea how this really went as no return value
        result = jp2iser.process(source, destination=destination, bounded_sizes=thumb_sizes, bounded_folder=thumb_dir,
                                 optimisation=optimisation)
        result["status"] = "Success"
        result["source"] = source
    else:
        result = {"status": "Job failed"}

    result["jobId"] = job_id

    return jsonify(result)

if __name__ == '__main__':
    app.run(threaded=True, debug=True)

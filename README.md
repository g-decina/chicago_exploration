# Chicago Business Density Explorer

> City of neighbourhoods or City of neighborhoods is a commonly applied nickname for many cities, and may refer to:
> 
> (...)
> 
> * **Chicago, Illinois, United States**, *see Community areas in Chicago*
> 
> (...)
> 
> *From Wikipedia*

**Does the data agree?**

# The Challenge: Messy Data

The City of Chicago's business licence dataset ([link](https://data.cityofchicago.org/Community-Economic-Development/Business-Licenses-Current-Active-Map/e4sp-itvq)) contains 2,404 unique activity codes and labels. These codes are manually entered and are, quite often, inconsistent. Here's an example:

* "Fitness Training On and Off Premises", "Fitness Classes", "Operation of a Health Club" are three different labels;
* There is a plethora of labels tied to personal care and beauty: "Hair Services", "Hair, Nail and Skin Care Services", "Nail Services", "Prove Waxing Services", etc. Many companies fall in several of these categories! Without knowing how their turnover is split between each category of services, we could well just brand them as "Personal Care". 

# The Solution

An automated ETL pipeline helped me structure this chaos.
1. **Semantic NLP Layer**. I used a Transformer-based embedding model to vectorize activity description.
2. **Agglomerative Clustering**. Groups of labels with similar semantic meaning are created, reducing the thousands of labels we would have to consider to only 41 broad categories.
3. **Geospatial Density (HDBSCAN)**. A density-based clustering algorithm identified "hot nodes" of commercial activity for the selected labels. This filters out spatial noise to reveal organic business districts.

Let's get back to our two examples. Our model automatically relabeled the first cluster as "Fitness Classes" and the second as "Hair Services", assessing that those two specific labels are at "the center" (so-to-speak) of their respective clusters.

# Tech Stack

* **Infrastructure**:Docker
* **Backend**: FastAPI
* **Frontend**: Streamlit, Folium
* **Data Science & Machine Learning**: GeoPandas, Scikit-Learn (Agglomerative Clustering, HDBSCAN), SentenceTransformers (SBERT)

# Quick Start

This project is containerized. You can run it as follows:

1. **Clone the repository**

`git clone [https://github.com/YOUR_USERNAME/chicago_exploration.git](https://github.com/YOUR_USERNAME/chicago_exploration.git)
cd chicago_exploration`

2. **Download the appropriate data**.

You can download the raw data [here](https://data.cityofchicago.org/Community-Economic-Development/Business-Licenses-Current-Active-Map/e4sp-itvq). You need to manually place it in the `/data/raw` folder.

3. **Run with Docker**

Use `docker-compose up --build` to launch the containerized application.

On the first run *without processed data*, the container will automatically run the NLP processing script. This usually takes a couple of seconds, but may take up to 1 minute depending on your hardware.

*Note that the version available on GitHub already features processed data in Arrow format!*

4. **Access the application!**

* Frontend: http://localhost:8501
* API Docs: http://localhost:8000/docs

# What's Next?

A lot of extra features can be added in the future:
* Using the Chicago Data Portal's API to automate the download of raw data on the first run.
* Training, and then incorporating a GNN (Graph Neural Network) layer to enable a more sophisticated clustering method based on spatial adjacency.

# About the Author

**Guillaume Decina** | Data Scientist & ML Engineer | Geospatial & Forecasting Specialist

[Find me on LinkedIn](https://www.linkedin.com/in/guillaume-d-8648261b1)

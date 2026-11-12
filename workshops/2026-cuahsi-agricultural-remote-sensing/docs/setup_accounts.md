# Before the session: three free accounts

The workshop runs entirely in a web browser. Three free accounts are needed, and creating them takes about 15 minutes in total. Please complete the steps before Thursday, November 12, 2026, because account registration is the usual source of delay in a hands-on session.

| Account | Used for | Guide |
|---|---|---|
| Google account | Running the notebooks in Google Colab, and saving your results in Google Drive | Section 1 below, then [google_colab.md](google_colab.md) |
| NASA Earthdata Login | Downloading the satellite imagery in notebook 2 | Section 2 below |
| Google Earth Engine | Publishing the crop map as a web app (the `GEE` folder), and the optional notebook 4 | [google_earth_engine_account.md](google_earth_engine_account.md) |

A GitHub account is not required. The repository is public, and the notebooks open in Colab without signing in to GitHub.

## 1. Google account and Google Colab

Any Google account works, personal or institutional.

1. Sign in to your Google account in the browser you will use during the workshop.
2. Open <https://colab.research.google.com>. If the welcome notebook loads, Colab is ready.
3. Check that your Google Drive has about 100 MB of free space. The notebooks save their result files there.

How the notebooks behave in Colab (the GPU setting, the Drive permission, the login prompts) is described in [google_colab.md](google_colab.md). Reading it once before the session is enough.

## 2. NASA Earthdata Login

The Harmonized Landsat Sentinel-2 imagery is open to any registered Earthdata user.

1. Open <https://urs.earthdata.nasa.gov> and choose **Register**.
2. Fill in the form and confirm your email address with the link NASA sends you.
3. Sign in once at <https://urs.earthdata.nasa.gov> to check that the username and password work. Notebook 2 asks for both.

No further approval is needed for the collection used in this workshop.

## 3. Google Earth Engine

Earth Engine access is given to a Google Cloud project that you register for noncommercial use. The registration is free and takes about five minutes. Follow [google_earth_engine_account.md](google_earth_engine_account.md), and write down the **project id** at the end.

## 4. Your computer

A laptop with a current web browser (Chrome, Firefox, Edge or Safari) is enough. All computation runs on Google's machines. Bring a charger. If your browser blocks pop-up windows, allow them for `colab.research.google.com`, because the Google Drive permission opens in a pop-up.

## Checklist

- [ ] Signed in to a Google account, and Colab opens a notebook
- [ ] Earthdata Login username and password tested
- [ ] Earth Engine project registered, Code Editor opens, project id written down
- [ ] Laptop, charger, current browser

## If something fails

Bring the exact error message to the session. The first minutes of the workshop are reserved for account problems. A participant without Earth Engine access can still complete notebooks 1 to 3, and a participant without an Earthdata Login can still complete notebooks 1 and 3 with the example crop map shipped in the `GEE` folder.

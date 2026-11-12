# Running the workshop in Google Colab

Google Colab is a free service that runs Jupyter notebooks on a Google cloud machine and shows them in your browser. The whole workshop runs there. You need a Google account and nothing else: no installation, no powerful laptop.

## Open a notebook

1. Sign in to your Google account in the browser.
2. On the workshop page of the repository, click the **Open in Colab** badge next to a notebook. The notebook opens in a new tab.
3. Colab may warn that the notebook was not authored by Google. Click **Run anyway**. The notebooks only read public data and write to your own Drive folder.

The notebook you opened is a temporary copy. To keep your own edits, choose **File**, **Save a copy in Drive**.

## Turn on the GPU (notebook 2)

The crop model runs about ten times faster on a GPU. Do this before running any cell of notebook 2, because changing it later restarts the machine.

1. In the menu, choose **Runtime**, then **Change runtime type**.
2. Under *Hardware accelerator*, select **T4 GPU**.
3. Click **Save**.

If no GPU is available at that moment, stay on CPU and keep `QUICK_DEMO = True` in notebook 2. Notebooks 1, 3 and 4 do not need a GPU.

## Run the cells

- Click a cell and press **Shift + Enter**, or click the play button at its left. Run the cells from top to bottom.
- The first cell of every notebook, *Setup*, copies the workshop code to the cloud machine and installs a few packages. It takes about one minute the first time.
- Avoid *Run all* in notebooks 2 and 4: they stop to ask for a login, and it is better to read each step.

## Let Colab save your results in Google Drive

Each notebook runs on its own temporary machine. A file written by notebook 2 is therefore invisible to notebook 3, unless it is stored somewhere shared. The Setup cell solves this by saving your results in your Google Drive, in a folder named `cuahsi_crop_map`.

When the Setup cell runs, Colab asks: *Permit this notebook to access your Google Drive files?*

1. Click **Connect to Google Drive**.
2. Choose your account.
3. Tick **Select all**, then click **Continue**. Without *Select all* the connection is refused.

You are asked once per notebook. The folder holds a few result files (the watershed boundary, the 18 band image stack, the crop map, the web map), about 75 MB in total for the whole default basin and less for the quick demonstration. The downloaded satellite granules stay on the temporary machine and do not use your Drive space.

If you prefer not to connect Drive, set `KEEP_RESULTS_IN_DRIVE = False` in the Setup cell. Notebooks 3 and 4 then continue with the example crop map shipped with the workshop.

## Log in to NASA Earthdata (notebook 2)

One cell asks for your Earthdata username and password. Type each one in the box that appears under the cell and press Enter. The password is not shown while you type. See [setup_accounts.md](setup_accounts.md) for creating the Earthdata account.

## Where the files are

- Click the **folder icon** on the left edge of Colab to browse the files of the cloud machine. The workshop code is in `nasa-nfews-iihr-public`, and your Drive is under `drive/MyDrive`.
- Notebook 3 downloads the results to your computer. The browser may ask permission to download several files at once: allow it.

## Good to know

| Situation | What happens | What to do |
|---|---|---|
| You leave the tab idle for a long time | Colab disconnects the machine | Click **Reconnect**, run the Setup cell again, and continue. Results saved in Drive are still there |
| A message about `HF_TOKEN` appears in notebook 2 | Colab notes that no Hugging Face token is set | Ignore it. The model is public |
| Red text scrolls during the Setup cell | Package installation notes | Ignore it unless the cell ends with an error |
| *You have reached your GPU limit* | The free GPU quota of your account is used up | Switch the runtime back to CPU and keep `QUICK_DEMO = True` |
| The Drive permission window does not appear | A pop-up blocker is active | Allow pop-ups for `colab.research.google.com` and run the cell again |

## The four notebooks

| Notebook | GPU | Logins asked |
|---|---|---|
| 1. Pick a basin | no | Google Drive |
| 2. Imagery and crop map | recommended | Google Drive, NASA Earthdata |
| 3. Visualize and export | no | Google Drive |
| 4. Check against the Cropland Data Layer (optional) | no | Google Earth Engine |

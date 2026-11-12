# Creating a Google Earth Engine account

Google Earth Engine is free for noncommercial use: research, teaching and nonprofit work. Access is given to a **Google Cloud project** that you register for Earth Engine, not to a person, so creating an account means two things: having a Google account, and registering one project. The registration takes about five minutes. Please do it before the workshop.

The screens below are the ones Google shows at the time of writing (November 2026). Labels change from time to time; if a screen looks different, Google's own guide is the reference: <https://developers.google.com/earth-engine/guides/access>.

## What you need

- A Google account. A personal Gmail account works. A university account works too if your institution allows Google Cloud projects; if it blocks them, use a personal account.
- A web browser. Nothing is installed.
- No credit card for the tier used here.

## Steps

1. **Open the registration page.** Go to <https://code.earthengine.google.com/register> and sign in with your Google account. If you have used Earth Engine before, open <https://code.earthengine.google.com> instead, click your account picture in the top right corner, and choose **Register a new Cloud Project**.

2. **Name the project.** On the registration page, type a project name you will recognize later, for example `earth-engine-workshop`. For a personal account, leave Organization and Location on **No organization**. Continue.

3. **Start the noncommercial check.** On the configuration page, click **Verify**. Earth Engine asks a few questions to confirm that your use is noncommercial.

4. **Choose the organization type.** If you are registering for this workshop, choose **Earth Engine trainer or trainee**, then **Next**. If you will use Earth Engine in your own research afterwards, you may choose the option that describes your institution instead, for example an academic or research institution.

5. **Check eligibility.** For the trainee option, set your role to **Participant** and enter the dates of the course: November 12, 2026 for both start and end. Click **Check eligibility**. A note confirms that you are eligible for noncommercial use. Click **Next**.

6. **Choose the plan.** Select the **Community** tier. It needs no billing account and its quota is more than enough for this workshop. The Contributor tier offers a higher quota but asks for a Cloud Billing account to verify identity; you can move to it later if you need it. Click **Next**.

7. **Describe your work.** Choose **Classroom or education** from the list (or the description that fits your research), then **Next**.

8. **Review and register.** Check the summary and click **Register**, then **Continue**.

## Check that it worked

Open <https://code.earthengine.google.com>. The Code Editor loads, and your project name is shown in the top right corner. Write down the **project id**: it is the lowercase name with hyphens shown there, for example `earth-engine-workshop-471203`. Notebook 4 asks for it, and it is part of every asset id and app address you create.

A quick test: paste the line below in the editor and click **Run**. The word `Hello` and an elevation value should appear in the Console tab.

```javascript
print('Hello', ee.Image('USGS/SRTMGL1_003').sample(ee.Geometry.Point([-92.33, 38.95]), 30).first().get('elevation'));
```

## If something goes wrong

| What you see | What to do |
|---|---|
| The registration page says your account cannot create projects | Your institution restricts Google Cloud. Sign out and register with a personal Google account |
| The Code Editor keeps showing the registration prompt | The registration was not completed. Open <https://code.earthengine.google.com/register> again and finish the last step |
| *Project is not registered to use Earth Engine* in notebook 4 | The project id is misspelled, or it is a different project from the one you registered. Copy the id from the top right corner of the Code Editor |
| You are asked for billing information | You selected the Contributor tier. Go back and choose Community |

## What you will use it for in the workshop

- **The `GEE` folder:** upload a crop map and a watershed boundary, paste one script, publish a public web app. This needs only the Code Editor.
- **Notebook 4 (optional):** compare the crop map with the USDA Cropland Data Layer from Python.

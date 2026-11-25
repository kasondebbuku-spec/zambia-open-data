# Deploying Zambia Open Data

The live site runs on two free services:

* **Neon**: PostgreSQL, the database.
* **Render**: two web services from [`render.yaml`](render.yaml). One is the API, built from the
  [`Dockerfile`](Dockerfile); the other is the explorer website in [`web/`](web).

Both deploy from `main`. Every merge to `main` redeploys them, and that includes the monthly
data refresh.

## 1. Create the database (Neon)

1. In the Neon console, create a project called `zambia-open-data`. Pick the **Frankfurt**
   region (AWS `eu-central-1`) so it sits next to Render's Frankfurt region.
2. Open **Connect**, turn **Connection pooling off**, and copy the connection string.
   * You need the *direct* string, whose host has no `-pooler` in it. The API's start-up
     migrations need it.
   * Keep this string private: anyone who has it can change the data.

## 2. Create the services (Render)

1. In Render, choose **New → Blueprint** and pick the `zambia-open-data` repository. Render
   reads `render.yaml` and shows two services, `zambia-open-data-api` and `zambia-open-data`.
2. It asks for two values:
   * `DATABASE_URL`: paste the Neon string from step 1.
   * `API_URL`: the API's public address, normally
     `https://zambia-open-data-api.onrender.com`.
     * If Render shows a different address for the API after it is created, change `API_URL`
       under the website's **Environment** tab.
3. Click **Apply** and wait for both services to go live.
   * On its first start the API's log shows `Loaded 483 rows from data/snapshot`.
   * Later starts print `already loaded; nothing to do`.
4. Check that it works:
   * `https://zambia-open-data-api.onrender.com/health` returns `{"status":"ok"}`.
   * The site's **About the data** page lists the quality checks and the CSV downloads.

Free Render services fall asleep after 15 minutes without visitors. The first visit after that
takes about a minute while the website and the API wake up. Switch both to the `starter` plan in
`render.yaml` if the site needs to answer straight away.

## 3. Turn on the monthly refresh (GitHub)

[`.github/workflows/refresh.yml`](.github/workflows/refresh.yml) runs on the 1st of each month.
It downloads the council's documents again, rebuilds the snapshot and runs every check.

* **The data changed:** it opens a pull request. Review the diff and merge it, and Render
  publishes the new data.
* **A check failed:** the run fails and GitHub emails you. Nothing is proposed.
* **Nothing changed:** it does nothing.

To let it open pull requests:

1. Go to the repository's **Settings → Actions → General → Workflow permissions**.
2. Tick **Allow GitHub Actions to create and approve pull requests**.
3. Test it once from **Actions → Monthly data refresh → Run workflow**.

Pull requests opened by the workflow don't trigger CI on their own. The refresh has already run
every quality check, and CI runs on `main` after you merge.

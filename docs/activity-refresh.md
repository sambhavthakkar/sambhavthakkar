# Activity-driven profile stats

The profile workflow refreshes on pushes to this repository, on `activity-ping`
dispatches, and every 30 minutes as a fallback. It commits only when a card
actually changes. The fallback also catches private activity and upstream card
updates that arrive after the original event.

To trigger a refresh from another repository you own:

1. Create a fine-grained personal access token restricted to the
   `sambhavthakkar/sambhavthakkar` repository, with **Contents: Read and write**.
   Give it an expiration and rotate it before expiry.
2. In each source repository, add that token as an Actions secret named
   `PROFILE_DISPATCH_TOKEN`.
3. Copy [`examples/notify-profile.yml`](../examples/notify-profile.yml) to
   `.github/workflows/notify-profile.yml` in each source repository.
4. Run **Notify profile stats** manually once in a source repository. A
   successful dispatch returns HTTP 204; verify that **Update stats** starts in
   the profile repository. A new commit appears only if the rendered cards
   differ.

The source workflow covers pushes, opened issues, opened or merged pull
requests, and submitted pull request reviews by `sambhavthakkar`. Add other
event types only if they affect the displayed stats. GitHub and the upstream
card services may update their counts after the event; the scheduled fallback
checks again. For a large number of repositories, replace the shared personal
token with a GitHub App installation token.

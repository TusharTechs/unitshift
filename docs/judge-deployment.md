# Judge deployment

The live historical evidence workspace is at https://ds59bjv2cezd6.cloudfront.net. The default route uses the licensed UCI and ECB data. The synthetic operations scenario stays separately labelled at `/sandbox`.

The app runs under systemd on a dedicated AWS EC2 t3.small instance with encrypted persistent storage. CloudFront provides public HTTPS. The origin only accepts the CloudFront managed network and the distribution origin header. Its final hop currently uses HTTP, so this public-data demonstration must not be used for private business data.

A dedicated instance role reads only the project source prefix in S3. A systemd timer refreshes the registered Zetaris source credentials every fifteen minutes using IMDSv2. Workstation AWS access keys are not installed on the host. Credentials and private deployment state are excluded from source control and the source archive.

## Nightshift runtime

The primary application, source reads, memory and Nebius Nemotron inference run in the cloud. The Nightshift desktop runtime runs on the user's Mac and is connected by a loopback-only encrypted reverse SSH bridge. The Mac, Nightshift and that bridge must remain running for the secondary review. The UI records unavailable secondary reviews explicitly. A supported unattended Nightshift endpoint is required before production deployment.

## Cost and retirement

The authorized initial judge deployment budget is USD 20, separate from model usage and the existing Zetaris cluster. The dedicated compute price checked during setup is USD 0.0208/hour. Standard CPU credits avoid unlimited burst charges. The ordinary initial fourteen-day base compute, public IPv4 and small volume estimate is below USD 20, while unusual traffic and API use can change total cost.

A systemd timer stops this instance on November 10, 2026 at 00:00 UTC. Stopped disk and distribution resources remain and require a later cleanup decision. Existing Zetaris infrastructure is outside this judge host estimate.

## Verification evidence

`data/evidence/deployment-verification.json` records the observed source counts, test results and accepted live run. `public-deployed-investigation.json` and `public-deployed-receipts.json` contain a recorded public investigation, including actual effective model IDs and the hash-linked receipt chain. The chain detects changes within a supplied transcript; it is not an externally notarized proof.

The source release passes 48 regression checks on macOS and Ubuntu. Three real-source examples demonstrate cancellation context, duplicate-looking cancellation rows and missing customer identity. This is not an independent accuracy benchmark or evidence of measured customer savings.

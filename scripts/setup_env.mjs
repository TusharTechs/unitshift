import fs from 'node:fs';
try {
  fs.copyFileSync('.env.example', '.env.local', fs.constants.COPYFILE_EXCL);
  fs.chmodSync('.env.local', 0o600);
  console.log('Created .env.local for this checkout. Add your own credentials only for live integrations.');
} catch (error) {
  if (error.code !== 'EEXIST') throw error;
  console.log('Existing .env.local left unchanged.');
}

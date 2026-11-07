# Final v1.1.0 packaging checklist — candidate checklist

Use FINAL110 and the explicit qualified inputs in BUILDING.md. Validate the reviewed source-export plan first. Build only after authorization; no EXE or source ZIP is created in Phase9E2. Refuse existing output paths rather than replace v1.0.0 or development artifacts.

After a final build: verify runtime/native and approved payload hashes, regenerate actual resource count/bundle/inventory, verify metadata and final EXE size/SHA-256, prepare the clean matching source ZIP with a newly generated source checksum inventory, and update RELEASE_ARTIFACTS.json from real results. Preserve individual optional licenses/source and all core/runtime notices. Validate both archives and public source contents; never copy private out/build/cache or transaction data.

Do not treat reference dev.3 hash/bundle/count as a final identity. Record owner passes separately from unverified recovery/DPI/clean-Windows checks; retain unsigned status. No Git publication is performed by this configuration.

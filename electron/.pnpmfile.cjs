// Allow build scripts for native Electron packages
function readPackage(pkg, context) {
  return pkg;
}

module.exports = {
  hooks: {
    readPackage,
  },
};

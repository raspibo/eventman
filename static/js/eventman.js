/** Utilities for EventMan. */

/* getTime method for string to convert them into Date objects. */
String.prototype.getTime = function() {
    var ms = Date.parse(this);
    return new Date(ms);
};      


/* UUID generator. */
function guid() {
    function s4() {
      return Math.floor((1 + Math.random()) * 0x10000).toString(16).substring(1);
    }
    return s4() + s4() + '-' + s4() + '-' + s4() + '-' + s4() + '-' + s4() + s4() + s4();
}

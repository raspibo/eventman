/** Utilities for EventMan. */

/* getTime method for string to convert them into Date objects. */
String.prototype.getTime = function() {
    var ms = Date.parse(this);
    return new Date(ms);
};      


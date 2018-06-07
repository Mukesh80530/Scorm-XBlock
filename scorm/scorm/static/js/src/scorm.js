/* Javascript for ScormXBlock. */
function ScormXBlock(runtime, element) {
    $('#scorm_story_btn', element).click(function(eventObject) {
		var story_container = $('#scorm_story_container');
		story_container.attr('src', story_container.data('src')).show();
		$(this).hide();
    });

    $(function ($) {
        /* Here's where you'd do things on page load. */
    });
}

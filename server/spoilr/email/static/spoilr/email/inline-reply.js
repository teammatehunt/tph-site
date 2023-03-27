for (const replyButton of document.querySelectorAll('.email-reply-button')) {
  const messageId = replyButton.dataset.messageId;
  if (!messageId) throw new Error('Missing reply button message ID');

  const replyForm = document.querySelector('#reply-form-' + messageId);

  const bodyTextarea = replyForm.querySelector('textarea');
  const messageIdField = replyForm.querySelector('[name=id]');
  const cancelButton = replyForm.querySelector('#cancel');

  replyForm.classList.toggle('hidden', true);

  replyButton.addEventListener('click', () => {
    replyForm.classList.toggle('hidden', false);
    messageIdField.value = messageId;
    bodyTextarea.value = '';
    bodyTextarea.focus();
  });

  cancelButton.addEventListener('click', () => {
    replyForm.classList.toggle('hidden', true);
    bodyTextarea.value = '';
    messageIdField.value = '';
  })
}
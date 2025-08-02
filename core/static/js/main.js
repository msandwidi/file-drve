document.addEventListener("DOMContentLoaded", function () {
  const toggleBtn = document.getElementById("menu-btn");
  const menu = document.getElementById("mobile-menu");

  if (toggleBtn && menu) {
    toggleBtn.addEventListener("click", function () {
      menu.classList.toggle("hidden");
    });
  }

  // form details page 
  const deleteFormBtn = document.getElementById('deleteFormBtn');
  const closeDeleteForm = document.getElementById('closeDeleteForm');
  const deleteFormDialog = document.getElementById('deleteFormDialog');

  const duplicateFormBtn = document.getElementById('duplicateFormBtn');
  const closeDuplicateForm = document.getElementById('closeDuplicateForm');
  const duplicateFormDialog = document.getElementById('duplicateFormDialog');

  const editFormBtn = document.getElementById('editFormBtn');
  const closeEditForm = document.getElementById('closeEditForm');
  const editFormDialog = document.getElementById('editFormDialog');

  const addNewFolderBtn = document.getElementById('addNewFolderBtn');
  const closeNewFolderBtn = document.getElementById('closeNewFolderBtn');
  const addNewFolderDialog = document.getElementById('addNewFolderDialog');

  const showAddContactGroupBtn = document.getElementById('showAddContactGroupBtn');
  const closeAddNewContactGroupForm = document.getElementById('closeAddNewContactGroupForm');
  const addNewContactGroupForm = document.getElementById('addNewContactGroupForm');

  const addNewGroupBtn = document.getElementById('addNewGroupBtn');
  const closeNewGroupBtn = document.getElementById('closeNewGroupBtn');
  const addNewGroupDialog = document.getElementById('addNewGroupDialog');

  const addNewContactBtn = document.getElementById('addNewContactBtn');
  const closeAddNewContactForm = document.getElementById('closeAddNewContactForm');
  const addNewContactForm = document.getElementById('addNewContactForm');

  const uploadFilesDialogBtn = document.getElementById('uploadFilesDialogBtn');
  const closeUploadFilesDialogBtn = document.getElementById('closeUploadFilesDialogBtn');
  const uploadFilesDialogForm = document.getElementById('uploadFilesDialog');

  const renameFileBtn = document.getElementById('renameFileBtn');
  const closeRenameFileBtn = document.getElementById('closeRenameFileBtn');
  const renameFileDialog = document.getElementById('renameFileDialog');

  renameFileBtn?.addEventListener('click', () => {
    renameFileDialog.showModal();
  });

  closeRenameFileBtn?.addEventListener('click', () => {
    renameFileDialog.close();
  });

  uploadFilesDialogBtn?.addEventListener('click', () => {
    uploadFilesDialogForm.showModal();
  });

  closeUploadFilesDialogBtn?.addEventListener('click', () => {
    uploadFilesDialogForm.close();
  });

  addNewContactBtn?.addEventListener('click', () => {
    addNewContactForm.showModal();
  });

  closeAddNewContactForm?.addEventListener('click', () => {
    addNewContactForm.close();
  });

  addNewGroupBtn?.addEventListener('click', () => {
    addNewGroupDialog.showModal();
  });

  closeNewGroupBtn?.addEventListener('click', () => {
    addNewGroupDialog.close();
  });

  showAddContactGroupBtn?.addEventListener('click', () => {
    addNewContactGroupForm.showModal();
  });

  closeAddNewContactGroupForm?.addEventListener('click', () => {
    addNewContactGroupForm.close();
  });

  addNewFolderBtn?.addEventListener('click', () => {
    addNewFolderDialog.showModal();
  });

  closeNewFolderBtn?.addEventListener('click', () => {
    addNewFolderDialog.close();
  });

  deleteFormBtn?.addEventListener('click', () => {
    deleteFormDialog.showModal();
  });

  closeDeleteForm?.addEventListener('click', () => {
    deleteFormDialog.close();
  });


  duplicateFormBtn?.addEventListener('click', () => {
    duplicateFormDialog.showModal();
  });

  closeDuplicateForm?.addEventListener('click', () => {
    duplicateFormDialog.close();
  });

  editFormBtn?.addEventListener('click', () => {
    editFormDialog.showModal();
  });

  closeEditForm?.addEventListener('click', () => {
    editFormDialog.close();
  });

  const editQuestionOptionDialog = document.getElementById('editQuestionOptionDialog');
  const closeEditTextQuestionDialog = document.getElementById('closeEditTextQuestionDialog');

  closeEditTextQuestionDialog?.addEventListener('click', () => {
    editQuestionOptionDialog.close();
  });

  document.querySelectorAll('.open-edit-dialog-btn').forEach(button => {
    button.addEventListener('click', () => {
      const questionId = button.getAttribute('data-question-id');

      editQuestionOptionDialog.showModal();
    });
  });

  //form details page end

});

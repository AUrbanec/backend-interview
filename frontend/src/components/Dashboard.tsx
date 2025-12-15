import { useEffect, useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { useNavigate } from 'react-router-dom'
import {
  Container,
  Paper,
  Typography,
  Button,
  Box,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  Checkbox,
  IconButton,
  TextField,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  CircularProgress,
  AppBar,
  Toolbar,
} from '@mui/material'
import { Delete as DeleteIcon, Add as AddIcon, Logout as LogoutIcon } from '@mui/icons-material'
import { signOut } from '../redux/slices/authSlice'
import {
  fetchTodos,
  createTodo,
  updateTodo,
  deleteTodo,
  Todo,
} from '../redux/slices/todosSlice'
import { AppDispatch, RootState } from '../redux/store/store'
import { useAuthContext } from '../auth/hooks'

const Dashboard = () => {
  const dispatch = useDispatch<AppDispatch>()
  const navigate = useNavigate()
  const { user } = useAuthContext()
  const { todos, loading } = useSelector((state: RootState) => state.todos)
  const [openDialog, setOpenDialog] = useState(false)
  const [newTodoTitle, setNewTodoTitle] = useState('')
  const [newTodoDescription, setNewTodoDescription] = useState('')

  useEffect(() => {
    dispatch(fetchTodos())
  }, [dispatch])

  const handleSignOut = async () => {
    await dispatch(signOut())
    navigate('/login')
  }

  const handleCreateTodo = async () => {
    if (newTodoTitle.trim()) {
      await dispatch(createTodo({ title: newTodoTitle, description: newTodoDescription }))
      setNewTodoTitle('')
      setNewTodoDescription('')
      setOpenDialog(false)
    }
  }

  const handleToggleComplete = async (todo: Todo) => {
    await dispatch(updateTodo({ id: todo.id, completed: !todo.completed }))
  }

  const handleDeleteTodo = async (id: string) => {
    await dispatch(deleteTodo(id))
  }

  return (
    <>
      <AppBar position="static">
        <Toolbar>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            Dashboard
          </Typography>
          <Typography variant="body2" sx={{ mr: 2 }}>
            {user?.email}
          </Typography>
          <IconButton color="inherit" onClick={handleSignOut}>
            <LogoutIcon />
          </IconButton>
        </Toolbar>
      </AppBar>

      <Container maxWidth="md" sx={{ mt: 4 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3 }}>
          <Typography variant="h5" component="h1">
            My Todos
          </Typography>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => setOpenDialog(true)}
          >
            Add Todo
          </Button>
        </Box>

        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
            <CircularProgress />
          </Box>
        ) : (
          <Paper>
            <List>
              {todos.length === 0 ? (
                <ListItem>
                  <ListItemText primary="No todos yet. Create your first todo!" />
                </ListItem>
              ) : (
                todos.map((todo) => (
                  <ListItem key={todo.id}>
                    <Checkbox
                      checked={todo.completed}
                      onChange={() => handleToggleComplete(todo)}
                    />
                    <ListItemText
                      primary={todo.title}
                      secondary={todo.description || 'No description'}
                      sx={{
                        textDecoration: todo.completed ? 'line-through' : 'none',
                        opacity: todo.completed ? 0.6 : 1,
                      }}
                    />
                    <ListItemSecondaryAction>
                      <IconButton
                        edge="end"
                        aria-label="delete"
                        onClick={() => handleDeleteTodo(todo.id)}
                      >
                        <DeleteIcon />
                      </IconButton>
                    </ListItemSecondaryAction>
                  </ListItem>
                ))
              )}
            </List>
          </Paper>
        )}
      </Container>

      <Dialog open={openDialog} onClose={() => setOpenDialog(false)}>
        <DialogTitle>Create New Todo</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Title"
            fullWidth
            variant="standard"
            value={newTodoTitle}
            onChange={(e) => setNewTodoTitle(e.target.value)}
            required
          />
          <TextField
            margin="dense"
            label="Description"
            fullWidth
            variant="standard"
            multiline
            rows={3}
            value={newTodoDescription}
            onChange={(e) => setNewTodoDescription(e.target.value)}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenDialog(false)}>Cancel</Button>
          <Button onClick={handleCreateTodo} variant="contained" disabled={!newTodoTitle.trim()}>
            Create
          </Button>
        </DialogActions>
      </Dialog>
    </>
  )
}

export default Dashboard

